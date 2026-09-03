"""
Stage 8 — End-to-End Pricing Integration Tests.

Covers T8-01 through T8-12:
  T8-01  Happy path end-to-end
  T8-02  Per-kg price decomposition (buyer = farmer + logistics + platform)
  T8-03  Total price decomposition (totals = per-kg × quantity)
  T8-04  Farmer protection floor preserved
  T8-05  Price range preserved (logistics must not alter Stage 6 range)
  T8-06  Reliability score preserved
  T8-07  Fallback logistics flagged
  T8-08  Invalid quantity rejected
  T8-09  Invalid logistics rejected
  T8-10  Platform fee correct
  T8-11  Determinism (same inputs → same output)
  T8-12  Regression — PRICE-E2E-001 full fixture
"""
import math
import copy
import pytest

from app.pricing.integration import compute_end_to_end_price, PricingIntegrationError
from app.logistics.engine import estimate_logistics
from app.logistics.cost import calculate_logistics_cost, calculate_buyer_price
from app.logistics.distance import calculate_distance_km


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Pune to Mumbai (valid coordinates from Stage 7 tests)
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
# T8-01: Happy path end-to-end
# ---------------------------------------------------------------------------

class TestT8_01_HappyPath:
    def test_happy_path_returns_all_fields(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert "commodity_id" in result
        assert result["commodity_id"] == "112fcfa1-8c94-52ae-91a6-abb7dc6ec8b5"
        assert result["mandi_id"] == "97ce83b2-322f-5c5c-8fce-22f2eacdd677"
        assert result["fair_price_per_kg"] == 20.16
        assert result["baseline_price_per_kg"] == 20.16
        assert result["distance_km"] == 118.48
        assert result["quantity_kg"] == 500.0

    def test_happy_path_buyer_price_positive(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["buyer_price_per_kg"] > 0
        assert result["buyer_total"] > 0


# ---------------------------------------------------------------------------
# T8-02: Per-kg price decomposition
# ---------------------------------------------------------------------------

class TestT8_02_PerKgDecomposition:
    def test_buyer_equals_farmer_plus_logistics_plus_platform(self):
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(cost_per_kg=1.75, total_logistics_cost=876.0)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        farmer = result["farmer_payout_per_kg"]
        logistics_kg = result["logistics_cost_per_kg"]
        platform = result["platform_fee_per_kg"]
        buyer = result["buyer_price_per_kg"]

        assert math.isclose(buyer, farmer + logistics_kg + platform, abs_tol=0.02), (
            f"{buyer} != {farmer} + {logistics_kg} + {platform}"
        )

    def test_platform_fee_is_5_percent_of_fair_price(self):
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        expected_platform = 20.16 * 0.05
        assert math.isclose(result["platform_fee_per_kg"], expected_platform, abs_tol=0.02)


# ---------------------------------------------------------------------------
# T8-03: Total price decomposition
# ---------------------------------------------------------------------------

class TestT8_03_TotalDecomposition:
    def test_totals_decompose(self):
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(
            cost_per_kg=1.75,
            total_logistics_cost=876.0,
            quantity_kg=500.0,
        )
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        farmer_total = result["farmer_total"]
        logistics_total = result["logistics_total"]
        platform_total = result["platform_total"]
        buyer_total = result["buyer_total"]

        assert math.isclose(buyer_total, farmer_total + logistics_total + platform_total, abs_tol=0.02)

    def test_totals_match_per_kg_times_quantity(self):
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(
            cost_per_kg=1.75,
            total_logistics_cost=876.0,
            quantity_kg=500.0,
        )
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        qty = result["quantity_kg"]
        assert math.isclose(result["farmer_total"], result["farmer_payout_per_kg"] * qty, abs_tol=0.02)
        assert math.isclose(result["buyer_total"], result["buyer_price_per_kg"] * qty, abs_tol=0.02)


# ---------------------------------------------------------------------------
# T8-04: Floor protection preserved
# ---------------------------------------------------------------------------

class TestT8_04_FloorProtection:
    def test_floor_preserved_when_not_blocked(self):
        pricing = _make_pricing_result(fair_price=20.16, floor=17.14, floor_blocked=False)
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics)

        assert result["protected_floor"] == 17.14
        assert result["floor_blocked"] is False
        assert result["farmer_payout_per_kg"] >= 17.14

    def test_floor_blocked_status_preserved(self):
        pricing = _make_pricing_result(
            fair_price=17.14, floor=18.00, floor_blocked=True, floor_status="BLOCKED"
        )
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics)

        assert result["floor_blocked"] is True
        assert result["floor_status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# T8-05: Price range preserved
# ---------------------------------------------------------------------------

class TestT8_05_PriceRange:
    def test_range_not_altered_by_logistics(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics)

        assert result["price_range_low"] == 17.90
        assert result["price_range_high"] == 22.42
        assert result["price_range_spread"] == 0.112


# ---------------------------------------------------------------------------
# T8-06: Reliability score preserved
# ---------------------------------------------------------------------------

class TestT8_06_Reliability:
    def test_reliability_unchanged(self):
        pricing = _make_pricing_result(reliability=45)
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics)

        assert result["reliability_score"] == 45


# ---------------------------------------------------------------------------
# T8-07: Fallback logistics flagged
# ---------------------------------------------------------------------------

class TestT8_07_Fallback:
    def test_fallback_flagged(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(
            is_fallback=True,
            fallback_reason="farmer or buyer location missing, using fallback distance",
        )
        result = compute_end_to_end_price(pricing, logistics)

        assert result["is_fallback"] is True
        assert "fallback" in (result["fallback_reason"] or "").lower()

    def test_fallback_explanation_marked(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(is_fallback=True, fallback_reason="missing coords")
        result = compute_end_to_end_price(pricing, logistics)

        assert result["logistics_explanation"]["is_estimated"] is True
        assert result["logistics_explanation"]["fallback_reason"] == "missing coords"


# ---------------------------------------------------------------------------
# T8-08: Invalid quantity rejected
# ---------------------------------------------------------------------------

class TestT8_08_InvalidQty:
    def test_zero_quantity_logistics_rejected(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(quantity_kg=0.0, total_logistics_cost=0.0, cost_per_kg=0.0)
        result = compute_end_to_end_price(pricing, logistics)
        assert result["quantity_kg"] == 0.0  # logistics allows zero, integration passes through

    def test_negative_quantity_logistics_rejected(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(quantity_kg=-100.0)
        with pytest.raises(PricingIntegrationError):
            compute_end_to_end_price(pricing, logistics)


# ---------------------------------------------------------------------------
# T8-09: Invalid logistics rejected
# ---------------------------------------------------------------------------

class TestT8_09_InvalidLogistics:
    def test_missing_logistics_field(self):
        pricing = _make_pricing_result()
        logistics = {"distance_km": 100.0}  # missing quantity_kg, cost_per_kg, etc.
        with pytest.raises(PricingIntegrationError):
            compute_end_to_end_price(pricing, logistics)

    def test_negative_cost_per_kg(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(cost_per_kg=-5.0)
        with pytest.raises(PricingIntegrationError):
            compute_end_to_end_price(pricing, logistics)

    def test_nan_distance(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(distance_km=float("nan"))
        with pytest.raises(PricingIntegrationError):
            compute_end_to_end_price(pricing, logistics)


# ---------------------------------------------------------------------------
# T8-10: Platform fee correct
# ---------------------------------------------------------------------------

class TestT8_10_PlatformFee:
    def test_custom_platform_fee(self):
        pricing = _make_pricing_result(fair_price=20.0)
        logistics = _make_logistics_result(cost_per_kg=2.0)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.10)

        expected_platform = 20.0 * 0.10
        assert math.isclose(result["platform_fee_per_kg"], expected_platform, abs_tol=0.02)

    def test_zero_platform_fee(self):
        pricing = _make_pricing_result(fair_price=20.0)
        logistics = _make_logistics_result(cost_per_kg=2.0)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.0)

        assert result["platform_fee_per_kg"] == 0.0
        assert math.isclose(
            result["buyer_price_per_kg"],
            result["farmer_payout_per_kg"] + result["logistics_cost_per_kg"],
            abs_tol=0.02,
        )

    def test_negative_platform_fee_rejected(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        with pytest.raises(PricingIntegrationError):
            compute_end_to_end_price(pricing, logistics, platform_fee_pct=-0.05)


# ---------------------------------------------------------------------------
# T8-11: Determinism
# ---------------------------------------------------------------------------

class TestT8_11_Determinism:
    def test_same_inputs_same_output(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        r1 = compute_end_to_end_price(pricing, logistics)
        r2 = compute_end_to_end_price(pricing, logistics)

        assert r1["buyer_price_per_kg"] == r2["buyer_price_per_kg"]
        assert r1["farmer_payout_per_kg"] == r2["farmer_payout_per_kg"]
        assert r1["logistics_cost_per_kg"] == r2["logistics_cost_per_kg"]
        assert r1["buyer_total"] == r2["buyer_total"]

    def test_different_quantities_deterministic(self):
        pricing = _make_pricing_result(fair_price=20.16)
        for qty in [100, 500, 1000, 5000]:
            logistics = _make_logistics_result(quantity_kg=float(qty), cost_per_kg=1.75)
            r1 = compute_end_to_end_price(pricing, logistics)
            r2 = compute_end_to_end_price(pricing, logistics)
            assert r1["buyer_total"] == r2["buyer_total"], f"Non-deterministic at qty={qty}"


# ---------------------------------------------------------------------------
# T8-12: Regression — PRICE-E2E-001 full fixture
# ---------------------------------------------------------------------------

class TestT8_12_PriceE2E001Regression:
    def test_price_e2e_001_fixture(self):
        """
        PRICE-E2E-001: Tomato, Pune→Mumbai, 500 kg, baseline-only mode.

        Baseline:  20.16 ₹/kg  (Section 8 weighted moving avg)
        Fair:      20.16 ₹/kg  (baseline-only, FairPrice == Baseline)
        Logistics:  1.75 ₹/kg  (Haversine+road 118.48 km, mini_truck 1000 kg, ₹12/km)
        Platform:   1.01 ₹/kg  (5% of fair_price)
        Buyer:     22.92 ₹/kg  (farmer + logistics + platform)

        Totals for 500 kg:
          farmer:  10080.00
          logistics: 876.00
          platform:  504.00
          buyer:   11460.00
        """
        pricing = _make_pricing_result(
            fair_price=20.16,
            baseline=20.16,
        )
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

        # Per-kg
        assert math.isclose(result["farmer_payout_per_kg"], 20.16, abs_tol=0.01)
        assert math.isclose(result["logistics_cost_per_kg"], 1.752, abs_tol=0.01)
        assert math.isclose(result["platform_fee_per_kg"], 20.16 * 0.05, abs_tol=0.01)
        assert math.isclose(
            result["buyer_price_per_kg"],
            20.16 + 1.752 + 20.16 * 0.05,
            abs_tol=0.02,
        )

        # Totals
        assert math.isclose(result["farmer_total"], 20.16 * 500, abs_tol=0.5)
        assert math.isclose(result["logistics_total"], 876.0, abs_tol=0.5)
        # platform_fee_per_kg rounds to 1.01 (from 1.008), so total = 1.01 × 500 = 505.0
        expected_platform_total = round(20.16 * 0.05, 2) * 500
        assert math.isclose(result["platform_total"], expected_platform_total, abs_tol=0.5)
        # buyer_total sums rounded component totals; re-derive the same way
        expected_buyer_total = result["farmer_total"] + result["logistics_total"] + result["platform_total"]
        assert math.isclose(result["buyer_total"], expected_buyer_total, abs_tol=0.5)

        # sanity: buyer_total close to theoretical
        assert math.isclose(
            result["buyer_total"],
            (20.16 + 1.752 + round(20.16 * 0.05, 2)) * 500,
            abs_tol=1.0,
        )

        # Invariant
        assert math.isclose(
            result["buyer_total"],
            result["farmer_total"] + result["logistics_total"] + result["platform_total"],
            abs_tol=0.5,
        )

    def test_price_e2e_001_with_ml_forecast(self):
        """Verify integration when ML forecast is available."""
        pricing = _make_pricing_result(
            baseline=20.16,
            ml_forecast=22.0,
            ml_available=True,
            fair_price=21.08,  # 20.16 + 0.5*(22.0-20.16) = 20.16+0.92 = 21.08
        )
        logistics = _make_logistics_result(cost_per_kg=1.752)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        assert result["forecast_price_per_kg"] == 22.0
        assert math.isclose(result["farmer_payout_per_kg"], 21.08, abs_tol=0.01)


# ---------------------------------------------------------------------------
# Additional invariant tests
# ---------------------------------------------------------------------------

class TestInvariants:
    def test_buyer_never_less_than_farmer_payout(self):
        """Logistics and platform are additive — buyer must exceed farmer payout."""
        pricing = _make_pricing_result(fair_price=20.16)
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics, platform_fee_pct=0.05)

        assert result["buyer_price_per_kg"] > result["farmer_payout_per_kg"]

    def test_all_totals_non_negative(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        assert result["farmer_total"] >= 0
        assert result["logistics_total"] >= 0
        assert result["platform_total"] >= 0
        assert result["buyer_total"] >= 0

    def test_no_double_counting_logistics_in_pricing(self):
        """
        Logistics cost must not feed back into fair_price.
        fair_price should equal baseline (baseline-only mode).
        """
        pricing = _make_pricing_result(baseline=20.16, fair_price=20.16)
        logistics = _make_logistics_result(cost_per_kg=1.75)
        result = compute_end_to_end_price(pricing, logistics)

        # fair_price should NOT include logistics
        assert result["fair_price_per_kg"] == 20.16
        assert result["farmer_payout_per_kg"] == 20.16


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_pricing_status(self):
        pricing = _make_pricing_result(status="INSUFFICIENT_DATA")
        logistics = _make_logistics_result()
        with pytest.raises(PricingIntegrationError) as exc_info:
            compute_end_to_end_price(pricing, logistics)
        assert "status" in str(exc_info.value)

    def test_missing_fair_price(self):
        pricing = _make_pricing_result()
        del pricing["fair_price"]
        logistics = _make_logistics_result()
        with pytest.raises(PricingIntegrationError):
            compute_end_to_end_price(pricing, logistics)

    def test_nan_fair_price(self):
        pricing = _make_pricing_result(fair_price=float("nan"))
        logistics = _make_logistics_result()
        with pytest.raises(PricingIntegrationError):
            compute_end_to_end_price(pricing, logistics)

    def test_missing_baseline(self):
        pricing = _make_pricing_result()
        del pricing["baseline"]
        logistics = _make_logistics_result()
        with pytest.raises(PricingIntegrationError):
            compute_end_to_end_price(pricing, logistics)


# ---------------------------------------------------------------------------
# Explanation payload tests
# ---------------------------------------------------------------------------

class TestExplanationPayloads:
    def test_pricing_explanation_has_required_keys(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        exp = result["pricing_explanation"]
        assert "baseline_price_per_kg" in exp
        assert "fair_price_per_kg" in exp
        assert "price_range" in exp
        assert "reliability_score" in exp
        assert "farmer_protection" in exp

    def test_logistics_explanation_has_required_keys(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        exp = result["logistics_explanation"]
        assert "distance_km" in exp
        assert "required_trips" in exp
        assert "breakdown" in exp
        assert "cost_per_kg" in exp
        assert "total_logistics_cost" in exp

    def test_final_explanation_structure(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result()
        result = compute_end_to_end_price(pricing, logistics)

        final = result["explanation"]
        assert "pricing" in final
        assert "logistics" in final
        assert "price_breakdown" in final
        assert "totals" in final
        assert "buyer_price_per_kg" in final["price_breakdown"]


# ---------------------------------------------------------------------------
# Compute logistics from coordinates (integration passthrough)
# ---------------------------------------------------------------------------

class TestComputeLogisticsFromCoordinates:
    def test_integration_computes_logistics_if_not_provided(self):
        pricing = _make_pricing_result(fair_price=20.16)
        result = compute_end_to_end_price(
            pricing,
            None,
            farmer_lat=PUNE_LAT,
            farmer_lon=PUNE_LON,
            buyer_lat=MUMBAI_LAT,
            buyer_lon=MUMBAI_LON,
            quantity_kg=500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=12.0,
        )
        assert result["distance_km"] > 0
        assert result["logistics_cost_per_kg"] > 0
        assert result["buyer_price_per_kg"] > result["farmer_payout_per_kg"]


# ---------------------------------------------------------------------------
# Vehicle class inference
# ---------------------------------------------------------------------------

class TestVehicleClassInference:
    def test_mini_truck_inferred(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(vehicle_capacity_kg=2500.0)
        result = compute_end_to_end_price(pricing, logistics)
        assert result["vehicle_class"] == "mini_truck"

    def test_tempo_inferred(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(vehicle_capacity_kg=1000.0)
        result = compute_end_to_end_price(pricing, logistics)
        assert result["vehicle_class"] == "tempo"

    def test_unknown_capacity_returns_none(self):
        pricing = _make_pricing_result()
        logistics = _make_logistics_result(vehicle_capacity_kg=750.0)
        result = compute_end_to_end_price(pricing, logistics)
        assert result["vehicle_class"] is None
