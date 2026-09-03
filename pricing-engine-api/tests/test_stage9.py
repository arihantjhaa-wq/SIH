"""
Stage 9 — FastAPI API Layer Tests.

Tests T9-01 through T9-16:
  T9-01  Health endpoint
  T9-02  Happy path pricing estimate
  T9-03  Final buyer price returned correctly
  T9-04  Price decomposition (farmer + logistics + platform = buyer)
  T9-05  Total decomposition (farmer_total + logistics_total + platform_total = buyer_total)
  T9-06  Price range preserved
  T9-07  Reliability score preserved
  T9-08  Logistics details exposed
  T9-09  Fallback metadata exposed
  T9-10  Invalid quantity rejected
  T9-11  Invalid coordinates rejected
  T9-12  Invalid platform fee rejected
  T9-13  Missing required data rejected
  T9-14  Internal pricing errors become structured API errors
  T9-15  Determinism (same request → same result)
  T9-16  Regression — Stage 0-8 tests remain intact
"""
import math
import copy
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.api.main import app
from app.pricing.integration import compute_end_to_end_price, PricingIntegrationError
from app.pricing.engine import predict_price
from app.logistics.engine import estimate_logistics
from app.logistics.cost import calculate_logistics_cost, calculate_buyer_price
from app.logistics.distance import calculate_distance_km


# ---------------------------------------------------------------------------
# Test Client
# ---------------------------------------------------------------------------

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Pune to Mumbai (valid coordinates from Stage 7/8 tests)
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
# T9-01: Health endpoint
# ---------------------------------------------------------------------------

class TestT9_01_Health:
    def test_health_returns_200(self):
        """GET /health should return 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self):
        """GET /health should return status: ok."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_json(self):
        """GET /health should return JSON."""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# T9-02: Happy path pricing estimate
# ---------------------------------------------------------------------------

class TestT9_02_HappyPath:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_happy_path_returns_200(self, mock_logistics, mock_predict):
        """Valid pricing request should return 200."""
        mock_predict.return_value = _make_pricing_result()
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

    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_happy_path_returns_all_required_fields(self, mock_logistics, mock_predict):
        """Valid pricing request should return all required fields."""
        mock_predict.return_value = _make_pricing_result()
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
        data = response.json()

        # Pricing fields
        assert "fair_price_per_kg" in data
        assert "farmer_payout_per_kg" in data
        assert "buyer_price_per_kg" in data

        # Logistics fields
        assert "distance_km" in data
        assert "logistics_cost_per_kg" in data

        # Platform fields
        assert "platform_fee_per_kg" in data

        # Explanation
        assert "explanation" in data

    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_happy_path_buyer_price_positive(self, mock_logistics, mock_predict):
        """Valid pricing request should return positive buyer price."""
        mock_predict.return_value = _make_pricing_result(fair_price=20.16)
        mock_logistics.return_value = _make_logistics_result(cost_per_kg=1.75)

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        data = response.json()
        assert data["buyer_price_per_kg"] > 0
        assert data["buyer_total"] > 0


# ---------------------------------------------------------------------------
# T9-03: Final buyer price
# ---------------------------------------------------------------------------

class TestT9_03_FinalBuyerPrice:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_buyer_price_correct(self, mock_logistics, mock_predict):
        """Buyer price should match expected calculation."""
        mock_predict.return_value = _make_pricing_result(fair_price=20.16)
        mock_logistics.return_value = _make_logistics_result(cost_per_kg=1.75)

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        data = response.json()

        # Expected: 20.16 + 1.75 + (20.16 * 0.05) = 22.92
        expected_buyer = 20.16 + 1.75 + (20.16 * 0.05)
        assert math.isclose(data["buyer_price_per_kg"], expected_buyer, abs_tol=0.1)


# ---------------------------------------------------------------------------
# T9-04: Price decomposition
# ---------------------------------------------------------------------------

class TestT9_04_PriceDecomposition:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_buyer_equals_farmer_plus_logistics_plus_platform(self, mock_logistics, mock_predict):
        """buyer_price_per_kg should equal farmer + logistics + platform."""
        mock_predict.return_value = _make_pricing_result(fair_price=20.16)
        mock_logistics.return_value = _make_logistics_result(cost_per_kg=1.75)

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        data = response.json()

        farmer = data["farmer_payout_per_kg"]
        logistics = data["logistics_cost_per_kg"]
        platform = data["platform_fee_per_kg"]
        buyer = data["buyer_price_per_kg"]

        assert math.isclose(buyer, farmer + logistics + platform, abs_tol=0.05)


# ---------------------------------------------------------------------------
# T9-05: Total decomposition
# ---------------------------------------------------------------------------

class TestT9_05_TotalDecomposition:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_totals_decompose(self, mock_logistics, mock_predict):
        """buyer_total should equal farmer_total + logistics_total + platform_total."""
        mock_predict.return_value = _make_pricing_result(fair_price=20.16)
        mock_logistics.return_value = _make_logistics_result(cost_per_kg=1.75, quantity_kg=500.0)

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        data = response.json()

        farmer_total = data["farmer_total"]
        logistics_total = data["logistics_total"]
        platform_total = data["platform_total"]
        buyer_total = data["buyer_total"]

        assert math.isclose(buyer_total, farmer_total + logistics_total + platform_total, abs_tol=0.5)


# ---------------------------------------------------------------------------
# T9-06: Price range preserved
# ---------------------------------------------------------------------------

class TestT9_06_PriceRange:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_range_preserved(self, mock_logistics, mock_predict):
        """Price range from Stage 6 should be preserved in API response."""
        mock_predict.return_value = _make_pricing_result()
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
        data = response.json()

        assert data["price_range_low"] == 17.90
        assert data["price_range_high"] == 22.42
        assert data["price_range_spread"] == 0.112


# ---------------------------------------------------------------------------
# T9-07: Reliability score preserved
# ---------------------------------------------------------------------------

class TestT9_07_Reliability:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_reliability_preserved(self, mock_logistics, mock_predict):
        """Reliability score from Stage 6 should be preserved."""
        mock_predict.return_value = _make_pricing_result(reliability=45)
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
        data = response.json()
        assert data["reliability_score"] == 45


# ---------------------------------------------------------------------------
# T9-08: Logistics details exposed
# ---------------------------------------------------------------------------

class TestT9_08_LogisticsDetails:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_logistics_exposed(self, mock_logistics, mock_predict):
        """Logistics details should be exposed in API response."""
        mock_predict.return_value = _make_pricing_result()
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
        data = response.json()

        assert data["distance_km"] == 118.48
        assert data["vehicle_capacity_kg"] == 1000.0
        assert data["required_trips"] == 1
        assert data["total_logistics_cost"] > 0
        assert data["logistics_cost_per_kg"] == 1.75


# ---------------------------------------------------------------------------
# T9-09: Fallback metadata exposed
# ---------------------------------------------------------------------------

class TestT9_09_Fallback:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_fallback_exposed(self, mock_logistics, mock_predict):
        """Fallback metadata should be exposed when logistics uses fallback."""
        mock_predict.return_value = _make_pricing_result()
        mock_logistics.return_value = _make_logistics_result(
            is_fallback=True,
            fallback_reason="farmer or buyer location missing, using fallback distance",
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
        data = response.json()

        assert data["is_fallback"] is True
        assert "fallback" in (data["fallback_reason"] or "").lower()


# ---------------------------------------------------------------------------
# T9-10: Invalid quantity rejected
# ---------------------------------------------------------------------------

class TestT9_10_InvalidQuantity:
    def test_zero_quantity_rejected(self):
        """Quantity of 0 should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 0.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_negative_quantity_rejected(self):
        """Negative quantity should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": -100.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 422

    def test_nan_quantity_rejected(self):
        """NaN quantity should be rejected — validated at schema level."""
        from pydantic import ValidationError
        from app.api.schemas.pricing import PricingRequest

        with pytest.raises(ValidationError):
            PricingRequest(
                commodity="Tomato",
                quantity_kg=float("nan"),
                farmer_location={"lat": PUNE_LAT, "lon": PUNE_LON},
                buyer_location={"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            )

    def test_infinite_quantity_rejected(self):
        """Infinite quantity should be rejected — validated at schema level."""
        from pydantic import ValidationError
        from app.api.schemas.pricing import PricingRequest

        with pytest.raises(ValidationError):
            PricingRequest(
                commodity="Tomato",
                quantity_kg=float("inf"),
                farmer_location={"lat": PUNE_LAT, "lon": PUNE_LON},
                buyer_location={"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            )


# ---------------------------------------------------------------------------
# T9-11: Invalid coordinates rejected
# ---------------------------------------------------------------------------

class TestT9_11_InvalidCoordinates:
    def test_invalid_latitude_rejected(self):
        """Latitude > 90 should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": 999, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 422

    def test_invalid_longitude_rejected(self):
        """Longitude > 180 should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": 999},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 422

    def test_missing_farmer_location_rejected(self):
        """Missing farmer location should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 422

    def test_missing_buyer_location_rejected(self):
        """Missing buyer location should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# T9-12: Invalid platform fee rejected
# ---------------------------------------------------------------------------

class TestT9_12_InvalidPlatformFee:
    def test_negative_platform_fee_rejected(self):
        """Negative platform fee should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
                "platform_fee_pct": -0.05,
            },
        )
        assert response.status_code == 422

    def test_platform_fee_above_1_rejected(self):
        """Platform fee > 1 should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
                "platform_fee_pct": 1.5,
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# T9-13: Missing required data rejected
# ---------------------------------------------------------------------------

class TestT9_13_MissingRequiredData:
    def test_missing_commodity_rejected(self):
        """Missing commodity should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 422

    def test_empty_commodity_rejected(self):
        """Empty commodity string should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 422

    def test_empty_body_rejected(self):
        """Empty request body should be rejected."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# T9-14: Internal pricing errors become structured API errors
# ---------------------------------------------------------------------------

class TestT9_14_InternalErrors:
    @patch("app.api.routes.pricing.predict_price")
    def test_unknown_commodity_returns_400(self, mock_predict):
        """Unknown commodity should return 400 with structured error."""
        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "UnknownCrop",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
            },
        )
        assert response.status_code == 400
        data = response.json()
        # FastAPI wraps HTTPException.detail under "detail" key
        error_data = data.get("detail", data)
        assert "error" in error_data
        assert error_data["error"]["code"] == "INVALID_COMMODITY"

    @patch("app.api.routes.pricing.predict_price")
    def test_pricing_integration_error_returns_400(self, mock_predict):
        """PricingIntegrationError should return 400 with structured error."""
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
        assert "error" in error_data
        assert error_data["error"]["code"] == "INSUFFICIENT_DATA"

    @patch("app.api.routes.pricing.predict_price")
    def test_unexpected_error_returns_500(self, mock_predict):
        """Unexpected errors should return 500 without stack trace."""
        mock_predict.side_effect = RuntimeError("Unexpected internal error")

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
        assert "error" in error_data
        assert error_data["error"]["code"] == "INTERNAL_ERROR"
        # Ensure no stack trace is exposed
        assert "traceback" not in str(data).lower()


# ---------------------------------------------------------------------------
# T9-15: Determinism
# ---------------------------------------------------------------------------

class TestT9_15_Determinism:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_same_request_same_result(self, mock_logistics, mock_predict):
        """Same request should return same calculated result."""
        mock_predict.return_value = _make_pricing_result()
        mock_logistics.return_value = _make_logistics_result()

        request_body = {
            "commodity": "Tomato",
            "quantity_kg": 500.0,
            "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
            "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
        }

        response1 = client.post("/api/v1/pricing/estimate", json=request_body)
        response2 = client.post("/api/v1/pricing/estimate", json=request_body)

        data1 = response1.json()
        data2 = response2.json()

        assert data1["buyer_price_per_kg"] == data2["buyer_price_per_kg"]
        assert data1["farmer_payout_per_kg"] == data2["farmer_payout_per_kg"]
        assert data1["logistics_cost_per_kg"] == data2["logistics_cost_per_kg"]
        assert data1["buyer_total"] == data2["buyer_total"]


# ---------------------------------------------------------------------------
# T9-16: Regression — existing tests remain intact
# ---------------------------------------------------------------------------

class TestT9_16_Regression:
    """Verify existing Stage 0-8 behavior remains intact."""

    def test_stage6_fair_price_formula_unchanged(self):
        """Stage 6 FairPrice formula should produce same results."""
        from app.pricing.discovery import calculate_fair_price

        # Baseline-only mode
        assert calculate_fair_price(20.16, None, 0.5) == 20.16
        # With ML forecast
        assert calculate_fair_price(20.16, 21.20, 0.5) == 20.68

    def test_stage7_logistics_cost_formula_unchanged(self):
        """Stage 7 logistics cost formula should produce same results."""
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
        assert result["cost_per_kg"] == pytest.approx(1.752, rel=0.01)

    def test_stage8_integration_formula_unchanged(self):
        """Stage 8 integration formula should produce same results."""
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(cost_per_kg=1.75, quantity_kg=500.0)

        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        # Verify price decomposition
        farmer = result["farmer_payout_per_kg"]
        logistics_kg = result["logistics_cost_per_kg"]
        platform = result["platform_fee_per_kg"]
        buyer = result["buyer_price_per_kg"]

        assert math.isclose(buyer, farmer + logistics_kg + platform, abs_tol=0.02)


# ---------------------------------------------------------------------------
# Additional tests
# ---------------------------------------------------------------------------

class TestOpenAPI:
    def test_openapi_json_available(self):
        """OpenAPI JSON should be available at /openapi.json."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "/api/v1/pricing/estimate" in data["paths"]
        assert "/health" in data["paths"]

    def test_docs_available(self):
        """Swagger UI should be available at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self):
        """ReDoc should be available at /redoc."""
        response = client.get("/redoc")
        assert response.status_code == 200


class TestRootEndpoint:
    def test_root_returns_api_info(self):
        """Root endpoint should return API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AgriDirect Pricing Engine API"
        assert data["version"] == "0.9.0"


class TestCustomPlatformFee:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_custom_platform_fee_applied(self, mock_logistics, mock_predict):
        """Custom platform fee should be applied correctly."""
        mock_predict.return_value = _make_pricing_result(fair_price=20.0)
        mock_logistics.return_value = _make_logistics_result(cost_per_kg=2.0)

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
                "platform_fee_pct": 0.10,
            },
        )
        data = response.json()

        expected_platform = 20.0 * 0.10
        assert math.isclose(data["platform_fee_per_kg"], expected_platform, abs_tol=0.02)


class TestFarmerDeclaredMinimum:
    @patch("app.api.routes.pricing.predict_price")
    @patch("app.api.routes.pricing.estimate_logistics")
    def test_farmer_minimum_passed_to_pricing(self, mock_logistics, mock_predict):
        """Farmer declared minimum should be passed to pricing engine."""
        mock_predict.return_value = _make_pricing_result(
            fair_price=20.16,
            floor=19.0,
            floor_status="OK",
        )
        mock_logistics.return_value = _make_logistics_result()

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "Tomato",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": PUNE_LAT, "lon": PUNE_LON},
                "buyer_location": {"lat": MUMBAI_LAT, "lon": MUMBAI_LON},
                "farmer_declared_minimum": 19.0,
            },
        )

        # Verify predict_price was called with farmer_declared_minimum
        call_kwargs = mock_predict.call_args[1]
        assert call_kwargs["farmer_declared_minimum"] == 19.0
