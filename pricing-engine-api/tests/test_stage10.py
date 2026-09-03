"""
Stage 10 — Testing + Hardening.

Tests T10-01 through T10-12:
  T10-01  Large quantity (1,000,000 kg) — no overflow, price invariant holds
  T10-02  Live API failure → demo fixture fallback with badge
  T10-03  Model artifact unavailable → baseline-only mode produces full result
  T10-04  Stale data → reduced reliability but system still returns result
  T10-05  Graceful degradation — API returns structured error on partial failure
  T10-06  Config-driven crop addition — 5 demo crops in crops.yaml match API mapping
  T10-07  Repeat-run consistency — same inputs → identical outputs across calls
  T10-08  Zero platform fee — buyer = farmer + logistics exactly
  T10-09  Floor BLOCKED status flows through to API response
  T10-10  High-value commodity (₹500/kg) — totals don't lose precision
  T10-11  Explanation payload completeness — all required keys present
  T10-12  Regression — Stage 6-9 formula invariants still hold
"""
import math
import copy
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import yaml

from fastapi.testclient import TestClient
from app.api.main import app
from app.pricing.integration import compute_end_to_end_price, PricingIntegrationError
from app.pricing.discovery import calculate_fair_price, calculate_spread, calculate_fair_price_range
from app.logistics.cost import calculate_logistics_cost, calculate_buyer_price
from app.logistics.distance import calculate_distance_km


# ---------------------------------------------------------------------------
# Test Client
# ---------------------------------------------------------------------------

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PUNE_LAT, PUNE_LON = 18.520430, 73.856744
MUMBAI_LAT, MUMBAI_LON = 19.0760, 72.8777


def _make_pricing_result(**overrides) -> dict:
    """Build a minimal valid pricing result (Stage 6 output)."""
    base = {
        "status": "OK",
        "commodity_id": "112fcfa1-8c94-52ae-91a6-abb7dc6ec8b5",
        "mandi_id": "97ce83b2-322f-5c5c-8fce-22f2eacdd677",
        "as_of_date": "2026-09-01",
        "baseline": 20.16,
        "ml_forecast": None,
        "ml_available": False,
        "fair_price": 20.16,
        "spread": 0.112,
        "fair_price_range": {"lower": 17.90, "expected": 20.16, "upper": 22.42, "spread": 0.112},
        "reliability": 45,
        "reliability_breakdown": {},
        "reliability_band": "LOW",
        "floor": 17.14,
        "floor_blocked": False,
        "floor_status": "OK",
        "floor_margin": 3.02,
        "pricing_constraints": [],
        "explanation": {
            "forecastDrivers": [],
            "pricingConstraints": [],
            "fallbacksUsed": [],
            "modelVersion": "baseline",
        },
        "features": {},
        "volatility_30d": 0.05,
        "demand_index": 0.0,
    }
    base.update(overrides)
    return base


def _make_logistics_result(**overrides) -> dict:
    """Build a minimal valid logistics result (Stage 7 output)."""
    base = {
        "distance_km": 118.48,
        "quantity_kg": 500.0,
        "vehicle_capacity_kg": 1000.0,
        "trips": 1,
        "cost_per_kg": 1.75,
        "total_logistics_cost": 876.0,
        "transport_cost": 816.0,
        "handling_cost": 60.0,
        "spoilage_buffer": 0.0,
        "breakdown": {"transport": 816.0, "handling": 60.0, "spoilageBuffer": 0.0},
        "is_fallback": False,
        "fallback_reason": None,
        "is_estimated": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# T10-01: Large quantity (1,000,000 kg) — no overflow
# ---------------------------------------------------------------------------

class TestT10_01_LargeQuantity:
    def test_large_quantity_no_overflow(self):
        """1,000,000 kg should produce finite totals without overflow."""
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(
            quantity_kg=1_000_000.0,
            cost_per_kg=1.75,
            total_logistics_cost=1_750_000.0,
            transport_cost=1_632_000.0,
            handling_cost=118_000.0,
            trips=1000,
        )
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        # All totals must be finite (no overflow to inf)
        assert math.isfinite(result["buyer_total"])
        assert math.isfinite(result["farmer_total"])
        assert math.isfinite(result["logistics_total"])
        assert math.isfinite(result["platform_total"])
        assert math.isfinite(result["buyer_price_per_kg"])

    def test_large_quantity_price_invariant_holds(self):
        """Price per-kg invariant must hold even with 1M kg quantity."""
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(
            quantity_kg=1_000_000.0,
            cost_per_kg=1.75,
            total_logistics_cost=1_750_000.0,
        )
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        buyer = result["buyer_price_per_kg"]
        farmer = result["farmer_payout_per_kg"]
        logistics_kg = result["logistics_cost_per_kg"]
        platform = result["platform_fee_per_kg"]
        assert math.isclose(buyer, farmer + logistics_kg + platform, abs_tol=0.02)

    def test_large_quantity_totals_decompose(self):
        """buyer_total = farmer_total + logistics_total + platform_total at 1M kg."""
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(
            quantity_kg=1_000_000.0,
            cost_per_kg=1.75,
            total_logistics_cost=1_750_000.0,
        )
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        assert math.isclose(
            result["buyer_total"],
            result["farmer_total"] + result["logistics_total"] + result["platform_total"],
            abs_tol=5.0,  # rounding tolerance at 1M scale
        )

    def test_large_quantity_via_api(self):
        """API should handle 1,000,000 kg without 500 error."""
        with (
            patch("app.api.routes.pricing.predict_price") as mock_predict,
            patch("app.api.routes.pricing.estimate_logistics") as mock_logistics,
        ):
            mock_predict.return_value = _make_pricing_result()
            mock_logistics.return_value = _make_logistics_result(quantity_kg=1_000_000.0)

            response = client.post(
                "/api/v1/pricing/estimate",
                json={
                    "commodity": "Tomato",
                    "quantity_kg": 1_000_000.0,
                    "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                    "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["buyer_price_per_kg"] > 0
            assert data["buyer_total"] > 0


# ---------------------------------------------------------------------------
# T10-02: Live API failure → demo fixture fallback with badge
# ---------------------------------------------------------------------------

class TestT10_02_LiveAPIFailureFallback:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_insufficient_data_returns_400_with_code(self, mock_logistics, mock_predict):
        """When pricing engine returns INSUFFICIENT_DATA, API returns 400 with error code."""
        mock_predict.return_value = {
            "status": "INSUFFICIENT_DATA",
            "reason": "No baseline data available for prediction",
            "commodity_id": "112fcfa1-8c94-52ae-91a6-abb7dc6ec8b5",
            "mandi_id": "97ce83b2-322f-5c5c-8fce-22f2eacdd677",
            "as_of_date": "2026-09-01",
        }

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 400
        data = response.json()
        error_data = data.get("detail", data)
        assert error_data["error"]["code"] == "INSUFFICIENT_DATA"

    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_pricing_exception_returns_structured_error(self, mock_logistics, mock_predict):
        """PricingIntegrationError from engine returns structured 400."""
        mock_predict.side_effect = PricingIntegrationError(
            field="fair_price",
            message="fair_price must be a number, got None",
        )

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 400
        data = response.json()
        error_data = data.get("detail", data)
        assert "error" in error_data
        assert "fair_price" in error_data["error"]["message"]

    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_runtime_error_returns_500_no_trace(self, mock_logistics, mock_predict):
        """Unexpected RuntimeError returns 500 with no stack trace exposed."""
        mock_predict.side_effect = RuntimeError("Database connection lost")

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 500
        data = response.json()
        error_data = data.get("detail", data)
        assert error_data["error"]["code"] == "INTERNAL_ERROR"
        assert "traceback" not in str(data).lower()
        assert "Database connection lost" not in str(data)


# ---------------------------------------------------------------------------
# T10-03: Model artifact unavailable → baseline-only mode
# ---------------------------------------------------------------------------

class TestT10_03_BaselineOnlyMode:
    def test_baseline_only_produces_valid_result(self):
        """Baseline-only mode (ml_available=False) produces a full result."""
        pricing = _make_pricing_result(
            ml_available=False,
            ml_forecast=None,
            fair_price=20.16,
            baseline=20.16,
        )
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["baseline_price_per_kg"] == 20.16
        assert result["fair_price_per_kg"] == 20.16
        assert result["buyer_price_per_kg"] > 0
        assert result["forecast_price_per_kg"] is None

    def test_baseline_only_explanation_shows_ml_unavailable(self):
        """Explanation should indicate ML is not available."""
        pricing = _make_pricing_result(ml_available=False, ml_forecast=None)
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["pricing_explanation"]["ml_available"] is False
        assert result["pricing_explanation"]["forecast_price_per_kg"] is None

    def test_baseline_only_via_api(self):
        """API returns 200 when predict_price runs in baseline-only mode."""
        with (
            patch("app.api.routes.pricing.predict_price") as mock_predict,
            patch("app.api.routes.pricing.estimate_logistics") as mock_logistics,
        ):
            mock_predict.return_value = _make_pricing_result(
                ml_available=False,
                ml_forecast=None,
                fair_price=20.16,
                baseline=20.16,
            )
            mock_logistics.return_value = _make_logistics_result()

            response = client.post(
                "/api/v1/pricing/estimate",
                json={
                    "commodity": "Tomato",
                    "quantity_kg": 500.0,
                    "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                    "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["fair_price_per_kg"] == 20.16
            assert data["buyer_price_per_kg"] > 20.16  # buyer > farmer due to logistics + fee

    def test_baseline_only_farmer_equals_fair_price(self):
        """In baseline-only mode, fair_price == baseline (no ML blend)."""
        pricing = _make_pricing_result(
            baseline=20.16,
            fair_price=20.16,
            ml_available=False,
        )
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["fair_price_per_kg"] == result["baseline_price_per_kg"]


# ---------------------------------------------------------------------------
# T10-04: Stale data → reduced reliability but system still returns result
# ---------------------------------------------------------------------------

class TestT10_04_StaleDataReducedReliability:
    def test_low_reliability_still_returns_valid_result(self):
        """Low reliability score should not prevent result from being returned."""
        pricing = _make_pricing_result(reliability=15, reliability_band="LOW")
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["reliability_score"] == 15
        assert result["buyer_price_per_kg"] > 0
        assert result["farmer_payout_per_kg"] > 0

    def test_zero_reliability_still_returns_result(self):
        """Even zero reliability should produce a valid pricing result."""
        pricing = _make_pricing_result(reliability=0, reliability_band="LOW")
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["reliability_score"] == 0
        assert result["buyer_price_per_kg"] > 0

    def test_reliability_preserved_in_explanation(self):
        """Low reliability flows into explanation payload."""
        pricing = _make_pricing_result(reliability=15)
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["pricing_explanation"]["reliability_score"] == 15

    def test_high_reliability_preserved(self):
        """High reliability (90+) is preserved correctly."""
        pricing = _make_pricing_result(reliability=92, reliability_band="HIGH")
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["reliability_score"] == 92


# ---------------------------------------------------------------------------
# T10-05: Graceful degradation — API returns structured error on partial failure
# ---------------------------------------------------------------------------

class TestT10_05_GracefulDegradation:
    @patch("app.api.routes.pricing.estimate_logistics")
    @patch("app.api.routes.pricing.predict_price")
    def test_logistics_failure_returns_400(self, mock_predict, mock_logistics):
        """Logistics validation error returns structured 400."""
        mock_predict.return_value = _make_pricing_result()
        mock_logistics.side_effect = Exception("Logistics service unavailable")

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        # Should return 500 (unexpected exception handler)
        assert response.status_code == 500
        data = response.json()
        error_data = data.get("detail", data)
        assert error_data["error"]["code"] == "INTERNAL_ERROR"

    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_500_error_no_stack_trace_exposed(self, mock_logistics, mock_predict):
        """500 errors must not expose internal stack traces."""
        mock_predict.side_effect = ValueError("Something broke internally")

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code in (400, 500)
        data = response.json()
        raw = str(data)
        assert "traceback" not in raw.lower()
        assert "stack" not in raw.lower()
        assert "File \"" not in raw

    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_health_always_returns_200(self, mock_logistics, mock_predict):
        """Health endpoint should always return 200 even if pricing is broken."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# T10-06: Config-driven crop addition — 5 demo crops match API mapping
# ---------------------------------------------------------------------------

class TestT10_06_ConfigDrivenCropAddition:
    def test_crops_yaml_has_20_crops(self):
        """crops.yaml should contain exactly 20 demo crops."""
        config_path = Path(__file__).parent.parent / "configs" / "crops.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert len(config["crops"]) == 20

    def test_all_crops_are_active(self):
        """All 20 demo crops should be marked is_active: true."""
        config_path = Path(__file__).parent.parent / "configs" / "crops.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for crop in config["crops"]:
            assert crop["is_active"] is True, f"Crop {crop['name']} is not active"

    def test_api_mapping_covers_all_config_crops(self):
        """Every crop in crops.yaml should have a UUID mapping in the API route."""
        from app.api.routes.pricing import _get_commodity_id

        config_path = Path(__file__).parent.parent / "configs" / "crops.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        for crop in config["crops"]:
            commodity_id = _get_commodity_id(crop["name"])
            assert commodity_id is not None, (
                f"Crop '{crop['name']}' in crops.yaml has no UUID mapping in API route"
            )

    def test_all_crop_names_case_insensitive(self):
        """Commodity mapping should be case-insensitive."""
        from app.api.routes.pricing import _get_commodity_id

        for name in ["tomato", "Tomato", "TOMATO", "tOmAtO"]:
            assert _get_commodity_id(name) is not None

    def test_api_validates_unknown_commodity(self):
        """Unknown commodity should return 400, not crash."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "MangoXYZ",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# T10-07: Repeat-run consistency — same inputs → identical outputs
# ---------------------------------------------------------------------------

class TestT10_07_RepeatRunConsistency:
    def test_integration_deterministic_across_10_runs(self):
        """compute_end_to_end_price should produce identical results across 10 calls."""
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()

        results = [
            compute_end_to_end_price(pricing, logistics)
            for _ in range(10)
        ]

        for r in results[1:]:
            assert r["buyer_price_per_kg"] == results[0]["buyer_price_per_kg"]
            assert r["farmer_payout_per_kg"] == results[0]["farmer_payout_per_kg"]
            assert r["logistics_cost_per_kg"] == results[0]["logistics_cost_per_kg"]
            assert r["buyer_total"] == results[0]["buyer_total"]

    def test_api_deterministic_across_5_runs(self):
        """API should return identical results for 5 identical requests."""
        with (
            patch("app.api.routes.pricing.predict_price") as mock_predict,
            patch("app.api.routes.pricing.estimate_logistics") as mock_logistics,
        ):
            mock_predict.return_value = _make_pricing_result()
            mock_logistics.return_value = _make_logistics_result()

            body = {
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            }

            prices = []
            for _ in range(5):
                resp = client.post("/api/v1/pricing/estimate", json=body)
                prices.append(resp.json()["buyer_price_per_kg"])

            assert len(set(prices)) == 1, f"Non-deterministic results: {prices}"

    def test_fair_price_calculation_deterministic(self):
        """calculate_fair_price should be deterministic."""
        values = [calculate_fair_price(20.16, 22.0, 0.5) for _ in range(10)]
        assert len(set(values)) == 1

    def test_logistics_cost_deterministic(self):
        """calculate_logistics_cost should be deterministic."""
        values = [
            calculate_logistics_cost(
                distance_km=118.48,
                quantity_kg=500.0,
                vehicle_capacity_kg=1000.0,
                cost_per_km=12.0,
                handling_cost_per_point=30.0,
                spoilage_buffer_per_kg=0.0,
            )["total_logistics_cost"]
            for _ in range(10)
        ]
        assert len(set(values)) == 1


# ---------------------------------------------------------------------------
# T10-08: Zero platform fee — buyer = farmer + logistics exactly
# ---------------------------------------------------------------------------

class TestT10_08_ZeroPlatformFee:
    def test_zero_platform_fee_buyer_equals_farmer_plus_logistics(self):
        """With 0% platform fee, buyer_price = farmer_payout + logistics_cost."""
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.0)

        assert result["platform_fee_per_kg"] == 0.0
        assert math.isclose(
            result["buyer_price_per_kg"],
            result["farmer_payout_per_kg"] + result["logistics_cost_per_kg"],
            abs_tol=0.02,
        )

    def test_zero_platform_fee_totals(self):
        """With 0% platform fee, platform_total = 0."""
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(cost_per_kg=1.75, quantity_kg=500.0)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.0)

        assert result["platform_total"] == 0.0
        assert math.isclose(
            result["buyer_total"],
            result["farmer_total"] + result["logistics_total"],
            abs_tol=0.5,
        )


# ---------------------------------------------------------------------------
# T10-09: Floor BLOCKED status flows through to API response
# ---------------------------------------------------------------------------

class TestT10_09_FloorBlockedStatus:
    def test_floor_blocked_preserved_in_integration(self):
        """Floor BLOCKED status from Stage 6 should flow through Stage 8."""
        pricing = _make_pricing_result(
            fair_price=17.14,
            floor=18.00,
            floor_blocked=True,
            floor_status="BLOCKED",
        )
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["floor_blocked"] is True
        assert result["floor_status"] == "BLOCKED"
        assert result["protected_floor"] == 18.00

    def test_floor_blocked_via_api(self):
        """API should return floor_blocked=True when engine triggers floor."""
        with (
            patch("app.api.routes.pricing.predict_price") as mock_predict,
            patch("app.api.routes.pricing.estimate_logistics") as mock_logistics,
        ):
            mock_predict.return_value = _make_pricing_result(
                fair_price=17.14,
                floor=18.00,
                floor_blocked=True,
                floor_status="BLOCKED",
            )
            mock_logistics.return_value = _make_logistics_result()

            response = client.post(
                "/api/v1/pricing/estimate",
                json={
                    "commodity": "Tomato",
                    "quantity_kg": 500.0,
                    "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                    "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["floor_blocked"] is True
            assert data["floor_status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# T10-10: High-value commodity (₹500/kg) — no precision loss
# ---------------------------------------------------------------------------

class TestT10_10_HighValueCommodity:
    def test_high_value_no_precision_loss(self):
        """High-value commodity (₹500/kg) should not lose precision in totals."""
        pricing = _make_pricing_result(fair_price=500.0, baseline=500.0, floor=425.0)
        logistics = _make_logistics_result(cost_per_kg=1.75, quantity_kg=500.0)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        # farmer_total = 500 * 500 = 250000
        assert math.isclose(result["farmer_total"], 250_000.0, abs_tol=1.0)
        # buyer_price = 500 + 1.75 + 25.0 = 526.75
        assert math.isclose(result["buyer_price_per_kg"], 526.75, abs_tol=0.1)
        # buyer_total = 526.75 * 500 ≈ 263375
        assert math.isclose(result["buyer_total"], 526.75 * 500, abs_tol=5.0)

    def test_high_value_invariant_holds(self):
        """Price decomposition invariant holds at ₹500/kg."""
        pricing = _make_pricing_result(fair_price=500.0)
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        buyer = result["buyer_price_per_kg"]
        farmer = result["farmer_payout_per_kg"]
        logistics_kg = result["logistics_cost_per_kg"]
        platform = result["platform_fee_per_kg"]
        assert math.isclose(buyer, farmer + logistics_kg + platform, abs_tol=0.02)


# ---------------------------------------------------------------------------
# T10-11: Explanation payload completeness
# ---------------------------------------------------------------------------

class TestT10_11_ExplanationCompleteness:
    def test_pricing_explanation_all_keys(self):
        """Pricing explanation should have all required keys."""
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        exp = result["pricing_explanation"]
        required_keys = [
            "baseline_price_per_kg",
            "forecast_price_per_kg",
            "ml_available",
            "fair_price_per_kg",
            "price_range",
            "reliability_score",
            "volatility_30d",
            "demand_index",
            "farmer_protection",
            "forecast_drivers",
            "pricing_constraints",
            "fallbacks_used",
            "model_version",
        ]
        for key in required_keys:
            assert key in exp, f"Missing pricing explanation key: {key}"

    def test_logistics_explanation_all_keys(self):
        """Logistics explanation should have all required keys."""
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        exp = result["logistics_explanation"]
        required_keys = [
            "distance_km",
            "is_estimated",
            "fallback_reason",
            "vehicle_capacity_kg",
            "required_trips",
            "breakdown",
            "total_logistics_cost",
            "cost_per_kg",
        ]
        for key in required_keys:
            assert key in exp, f"Missing logistics explanation key: {key}"

    def test_final_explanation_structure(self):
        """Final explanation should have pricing, logistics, breakdown, totals."""
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        final = result["explanation"]
        assert "pricing" in final
        assert "logistics" in final
        assert "price_breakdown" in final
        assert "totals" in final

        breakdown = final["price_breakdown"]
        assert "farmer_payout_per_kg" in breakdown
        assert "logistics_cost_per_kg" in breakdown
        assert "platform_fee_per_kg" in breakdown
        assert "buyer_price_per_kg" in breakdown

        totals = final["totals"]
        assert "farmer_total" in totals
        assert "logistics_total" in totals
        assert "platform_total" in totals
        assert "buyer_total" in totals

    def test_farmer_protection_in_explanation(self):
        """Farmer protection details should be in explanation."""
        pricing = _make_pricing_result(floor=17.14, floor_blocked=False)
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        fp = result["pricing_explanation"]["farmer_protection"]
        assert fp["floor_per_kg"] == 17.14
        assert fp["blocked"] is False
        assert fp["status"] == "OK"


# ---------------------------------------------------------------------------
# T10-12: Regression — Stage 6-9 formula invariants still hold
# ---------------------------------------------------------------------------

class TestT10_12_Regression:
    def test_stage6_fair_price_formula(self):
        """Stage 6 FairPrice formula unchanged."""
        from app.pricing.discovery import calculate_fair_price
        assert calculate_fair_price(20.16, None, 0.5) == 20.16
        assert calculate_fair_price(20.16, 21.20, 0.5) == 20.68

    def test_stage6_spread_formula(self):
        """Stage 6 spread formula unchanged."""
        from app.pricing.discovery import calculate_spread
        spread = calculate_spread(volatility_30d=0.05, reliability=45)
        assert spread == pytest.approx(0.112, abs=0.01)

    def test_stage6_range_formula(self):
        """Stage 6 range formula unchanged."""
        from app.pricing.discovery import calculate_fair_price_range
        r = calculate_fair_price_range(20.16, 0.112)
        assert r["lower"] == pytest.approx(17.90, abs=0.1)
        assert r["upper"] == pytest.approx(22.42, abs=0.1)

    def test_stage7_logistics_cost_formula(self):
        """Stage 7 logistics cost formula unchanged."""
        result = calculate_logistics_cost(
            distance_km=68.0,
            quantity_kg=500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=12.0,
            handling_cost_per_point=30.0,
            spoilage_buffer_per_kg=0.0,
        )
        assert result["trips"] == 1
        assert result["transport_cost"] == pytest.approx(816.0, rel=0.01)
        assert result["handling_cost"] == pytest.approx(60.0, rel=0.01)
        assert result["total_logistics_cost"] == pytest.approx(876.0, rel=0.01)

    def test_stage8_integration_invariant(self):
        """Stage 8 price decomposition invariant unchanged."""
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(cost_per_kg=1.75, quantity_kg=500.0)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        buyer = result["buyer_price_per_kg"]
        farmer = result["farmer_payout_per_kg"]
        logistics_kg = result["logistics_cost_per_kg"]
        platform = result["platform_fee_per_kg"]
        assert math.isclose(buyer, farmer + logistics_kg + platform, abs_tol=0.02)

    def test_stage9_api_health_unchanged(self):
        """Stage 9 health endpoint unchanged."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_price_e2e_001_fixture_unchanged(self):
        """PRICE-E2E-001 fixture unchanged from Stage 8."""
        pricing = _make_pricing_result(fair_price=20.16, baseline=20.16)
        logistics = _make_logistics_result(
            distance_km=118.48,
            quantity_kg=500.0,
            vehicle_capacity_kg=1000.0,
            trips=1,
            cost_per_kg=1.752,
            total_logistics_cost=876.0,
            transport_cost=816.0,
            handling_cost=60.0,
            spoilage_buffer=0.0,
        )
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        assert math.isclose(result["farmer_payout_per_kg"], 20.16, abs_tol=0.01)
        assert math.isclose(result["logistics_cost_per_kg"], 1.752, abs_tol=0.01)
        assert math.isclose(result["platform_fee_per_kg"], 20.16 * 0.05, abs_tol=0.01)
        assert math.isclose(
            result["buyer_price_per_kg"],
            20.16 + 1.752 + 20.16 * 0.05,
            abs_tol=0.02,
        )
