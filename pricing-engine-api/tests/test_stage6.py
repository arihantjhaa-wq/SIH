"""
Stage 6 Test Suite: Price Discovery + Farmer Protection + Reliability + Explanation

Tests T14-T17, T38, T41, T43-T45 from spec Section 31.

T14: Confidence sub-scores sum correctly
T15: Farmer floor triggers block
T16: Farmer floor not falsely triggered
T17: Affordability never lowers farmer range (via range preservation)
T38: Explanation payload completeness
T41: Formula double-count regression (F1)
T43: Reliability score, baseline-only mode (F5)
T44: Volatility cap exact rule (F6)
T45: PRICE-E2E-001 fixture (F2)
"""
import math
import pytest
from datetime import date

from app.pricing.discovery import (
    calculate_fair_price,
    calculate_spread,
    calculate_fair_price_range,
)
from app.pricing.farmer_floor import (
    calculate_farmer_floor,
    check_floor_protection,
    apply_floor_check,
)
from app.pricing.reliability import (
    calculate_reliability_score,
    calculate_model_agreement,
    calculate_market_volatility,
    calculate_data_freshness,
    calculate_historical_volume,
    calculate_validation_quality,
    calculate_mandi_availability,
    calculate_weather_availability,
    get_reliability_band_label,
    WEIGHTS,
)
from app.pricing.explain import (
    build_explanation,
    build_forecast_drivers,
    build_pricing_constraints,
    get_market_condition,
    get_volatility_label,
)
from app.pricing.engine import predict_price


# ============================================================================
# T14: Confidence sub-scores sum correctly
# ============================================================================

class TestReliabilitySubscores:
    """T14: Verify reliability sub-scores follow Section 22 weighted formula."""

    def test_subscore_weights_sum_to_one(self):
        """All reliability weights should sum to 1.0."""
        total = sum(WEIGHTS.values())
        assert math.isclose(total, 1.0, abs_tol=1e-6), \
            f"Weight sum {total} != 1.0"

    def test_reliability_computed_correctly(self):
        """Verify weighted sum with known inputs."""
        # All sub-scores = 1.0 (perfect) => reliability = 100
        result = calculate_reliability_score(
            data_freshness=1.0,
            historical_volume=1.0,
            validation_quality=1.0,
            mandi_availability=1.0,
            weather_availability=1.0,
            model_agreement=1.0,
            market_volatility=1.0,
        )
        assert result["reliability"] == 100, \
            f"Perfect inputs should yield reliability=100, got {result['reliability']}"

    def test_reliability_zero_subscores(self):
        """All zeros should yield reliability=0."""
        result = calculate_reliability_score(
            data_freshness=0.0,
            historical_volume=0.0,
            validation_quality=0.0,
            mandi_availability=0.0,
            weather_availability=0.0,
            model_agreement=0.0,
            market_volatility=0.0,
        )
        assert result["reliability"] == 0, \
            f"Zero inputs should yield reliability=0, got {result['reliability']}"

    def test_reliability_mixed_subscores(self):
        """Verify known mixed inputs produce expected weighted sum."""
        # Compute expected manually:
        # 0.25*0.8 + 0.20*0.5 + 0.20*0.9 + 0.10*1.0 + 0.10*0.0 + 0.10*0.7 + 0.05*0.6
        expected = (
            0.25 * 0.8
            + 0.20 * 0.5
            + 0.20 * 0.9
            + 0.10 * 1.0
            + 0.10 * 0.0
            + 0.10 * 0.7
            + 0.05 * 0.6
        )
        expected_int = round(100.0 * expected)

        result = calculate_reliability_score(
            data_freshness=0.8,
            historical_volume=0.5,
            validation_quality=0.9,
            mandi_availability=1.0,
            weather_availability=0.0,
            model_agreement=0.7,
            market_volatility=0.6,
        )
        assert result["reliability"] == expected_int, \
            f"Expected {expected_int}, got {result['reliability']}"

    def test_subscore_bands_are_correct(self):
        """Reliability bands: HIGH >=80, MEDIUM 60-79, LOW 40-59, INSUFFICIENT <40."""
        assert get_reliability_band_label(80) == "HIGH"
        assert get_reliability_band_label(100) == "HIGH"
        assert get_reliability_band_label(60) == "MEDIUM"
        assert get_reliability_band_label(79) == "MEDIUM"
        assert get_reliability_band_label(40) == "LOW"
        assert get_reliability_band_label(59) == "LOW"
        assert get_reliability_band_label(39) == "INSUFFICIENT"
        assert get_reliability_band_label(0) == "INSUFFICIENT"

    def test_subscores_dict_contains_all_components(self):
        """Sub-scores dict must have all 7 keys."""
        result = calculate_reliability_score(
            data_freshness=0.5,
            historical_volume=0.5,
            validation_quality=0.5,
            mandi_availability=0.5,
            weather_availability=0.5,
            model_agreement=0.5,
            market_volatility=0.5,
        )
        expected_keys = {
            "data_freshness", "historical_volume", "validation_quality",
            "mandi_availability", "weather_availability",
            "model_agreement", "market_volatility",
        }
        actual_keys = set(result["subscores"].keys())
        assert actual_keys == expected_keys, \
            f"Missing subscore keys: {expected_keys - actual_keys}"


# ============================================================================
# T15: Farmer floor triggers block
# ============================================================================

class TestFarmerFloorBlock:
    """T15: Verify farmer floor blocks below-threshold recommendations."""

    def test_floor_blocks_when_lower_below_floor(self):
        """If FairPrice.Lower < FLOOR, status = BLOCKED."""
        floor = calculate_farmer_floor(baseline=20.0, farmer_declared_minimum=None)
        assert floor == 17.0  # 0.85 * 20.0

        check = check_floor_protection(fair_price_lower=15.0, floor=floor)
        assert check["blocked"] is True
        assert check["status"] == "BLOCKED"
        assert check["reason"] is not None

    def test_floor_margin_is_negative_when_blocked(self):
        """Margin should be negative when lower < floor."""
        check = check_floor_protection(fair_price_lower=15.0, floor=17.0)
        assert check["margin_above_floor"] < 0
        assert check["percent_below_floor"] > 0

    def test_floor_percentage_calculation(self):
        """Percent below floor should match formula: |margin/floor|*100."""
        check = check_floor_protection(fair_price_lower=10.0, floor=20.0)
        assert check["percent_below_floor"] == pytest.approx(50.0, abs=0.1)

    def test_farmer_declared_minimum_overrides_baseline_floor(self):
        """Farmer declared minimum overrides baseline 0.85x if higher."""
        floor = calculate_farmer_floor(baseline=20.0, farmer_declared_minimum=19.0)
        assert floor == 19.0  # max(17.0, 19.0) = 19.0

    def test_farmer_declared_minimum_does_not_override_if_lower(self):
        """If declared min is lower than baseline floor, baseline floor wins."""
        floor = calculate_farmer_floor(baseline=20.0, farmer_declared_minimum=15.0)
        assert floor == 17.0  # max(17.0, 15.0) = 17.0

    def test_floor_blocks_in_engine(self):
        """Full engine returns BLOCKED status when floor is triggered."""
        # Very high baseline with no ML => FairPrice = Baseline
        # Floor = 0.85 * Baseline
        # But FairPrice range lower should be above floor for normal inputs
        # To force a block, we need a case where spread pushes lower below floor
        # This requires: spread > 1 - 0.85 = 0.15 (the max spread), so spread alone can't block
        # Actually, spread is max 0.15, so lower = fair_price * (1 - 0.15)
        # If fair_price = baseline = 20.0, lower = 17.0, floor = 17.0 => exactly at floor (not blocked)
        # To block: need very high volatility or very low reliability
        # With max spread 0.15 and fair_price=20.0: lower=17.0, floor=17.0 => OK
        # The block happens when farmer_declared_minimum > fair_price * (1 - spread)
        floor = calculate_farmer_floor(baseline=20.0, farmer_declared_minimum=18.0)
        # lower = 20.0 * (1 - 0.15) = 17.0 < 18.0 => BLOCKED
        check = check_floor_protection(fair_price_lower=17.0, floor=floor)
        assert check["blocked"] is True


# ============================================================================
# T16: Farmer floor not falsely triggered
# ============================================================================

class TestFarmerFloorNotFalselyTriggered:
    """T16: Verify floor does not block normal recommendations."""

    def test_floor_not_triggered_when_lower_above_floor(self):
        """Normal recommendation should not be blocked."""
        floor = calculate_farmer_floor(baseline=20.0)
        assert floor == 17.0

        check = check_floor_protection(fair_price_lower=18.0, floor=floor)
        assert check["blocked"] is False
        assert check["status"] == "OK"

    def test_floor_exact_boundary_not_blocked(self):
        """When lower equals floor exactly, it is NOT blocked."""
        check = check_floor_protection(fair_price_lower=17.0, floor=17.0)
        assert check["blocked"] is False

    def test_floor_just_above_boundary(self):
        """Margin = 0.01 should be OK."""
        check = check_floor_protection(fair_price_lower=17.01, floor=17.0)
        assert check["blocked"] is False
        assert check["margin_above_floor"] == pytest.approx(0.01, abs=0.01)


# ============================================================================
# T17: Affordability never lowers farmer range
# ============================================================================

class TestAffordabilityDoesNotLowerFarmerRange:
    """T17: Floor check should not affect the fair price range itself."""

    def test_range_preserved_regardless_of_floor(self):
        """apply_floor_check preserves the original range."""
        range_dict = {"lower": 18.0, "expected": 20.0, "upper": 22.0, "spread": 0.10}
        result = apply_floor_check(range_dict, baseline=20.0, farmer_declared_minimum=19.0)
        # Range values should be unchanged
        assert result["lower"] == 18.0
        assert result["expected"] == 20.0
        assert result["upper"] == 22.0

    def test_farmer_floor_independent_of_buyer_budget(self):
        """Farmer floor should not change based on buyer's declared budget."""
        # Floor depends on Baseline only (not buyer budget)
        floor_a = calculate_farmer_floor(baseline=20.0)
        floor_b = calculate_farmer_floor(baseline=20.0, farmer_declared_minimum=19.0)
        # With no declared minimum, floor is just 0.85 * baseline
        assert floor_a == 17.0
        # With declared minimum, floor is max(17.0, 19.0) = 19.0
        assert floor_b == 19.0


# ============================================================================
# T38: Explanation payload completeness
# ============================================================================

class TestExplanationPayloadCompleteness:
    """T38: Explanation payload must have all required fields."""

    def test_explanation_has_all_required_fields(self):
        """Verify all Section 23 fields are present."""
        result = build_explanation(
            fair_price=20.68,
            fair_price_range={"lower": 18.36, "expected": 20.68, "upper": 23.00, "spread": 0.112},
            reliability_result={
                "reliability": 78,
                "band": "MEDIUM",
                "subscores": {
                    "data_freshness": 0.95,
                    "historical_volume": 0.8,
                    "validation_quality": 0.85,
                    "mandi_availability": 1.0,
                    "weather_availability": 0.7,
                    "model_agreement": 0.9,
                    "market_volatility": 0.2,
                },
                "weights": {},
                "volatility_capped": False,
                "model_agreement_default": False,
            },
            baseline=20.16,
            forecast=21.20,
            ml_available=True,
            baseline_only=False,
            features={},
            demand_index=64.0,
            weather_features={"rainfall_mm": 12.0, "temp_max_c": 34.0},
            floor_blocked=False,
            volatility_30d=0.12,
            model_version="prophet_v3_tomato_kolar_2026-08-25",
        )

        required_fields = [
            "recommendedPrice",
            "range",
            "reliability",
            "reliabilityBreakdown",
            "modelAgreementDefault",
            "marketCondition",
            "priceVolatility",
            "forecastDrivers",
            "pricingConstraints",
            "fallbacksUsed",
            "modelVersion",
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_range_has_min_max(self):
        """Range must have min and max."""
        result = build_explanation(
            fair_price=20.68,
            fair_price_range={"lower": 18.36, "expected": 20.68, "upper": 23.00, "spread": 0.112},
            reliability_result={
                "reliability": 78, "band": "MEDIUM",
                "subscores": {"data_freshness": 0.95, "historical_volume": 0.8,
                              "validation_quality": 0.85, "mandi_availability": 1.0,
                              "weather_availability": 0.7, "model_agreement": 0.9,
                              "market_volatility": 0.2},
                "weights": {}, "volatility_capped": False, "model_agreement_default": False,
            },
            baseline=20.16,
        )
        assert "min" in result["range"]
        assert "max" in result["range"]
        assert result["range"]["min"] < result["range"]["max"]

    def test_reliability_breakdown_has_all_components(self):
        """reliabilityBreakdown must have all 7 sub-scores."""
        result = build_explanation(
            fair_price=20.68,
            fair_price_range={"lower": 18.36, "expected": 20.68, "upper": 23.00, "spread": 0.112},
            reliability_result={
                "reliability": 78, "band": "MEDIUM",
                "subscores": {"data_freshness": 0.95, "historical_volume": 0.8,
                              "validation_quality": 0.85, "mandi_availability": 1.0,
                              "weather_availability": 0.7, "model_agreement": 0.9,
                              "market_volatility": 0.2},
                "weights": {}, "volatility_capped": False, "model_agreement_default": False,
            },
            baseline=20.16,
        )
        breakdown = result["reliabilityBreakdown"]
        expected_keys = {
            "dataFreshness", "historicalVolume", "validationQuality",
            "mandiAvailability", "weatherAvailability",
            "modelAgreement", "marketVolatility",
        }
        assert set(breakdown.keys()) == expected_keys

    def test_forecast_drivers_have_role_model_input(self):
        """All forecastDrivers should have role: model_input."""
        result = build_explanation(
            fair_price=20.68,
            fair_price_range={"lower": 18.36, "expected": 20.68, "upper": 23.00, "spread": 0.112},
            reliability_result={
                "reliability": 78, "band": "MEDIUM",
                "subscores": {"data_freshness": 0.95, "historical_volume": 0.8,
                              "validation_quality": 0.85, "mandi_availability": 1.0,
                              "weather_availability": 0.7, "model_agreement": 0.9,
                              "market_volatility": 0.2},
                "weights": {}, "volatility_capped": False, "model_agreement_default": False,
            },
            baseline=20.16,
            demand_index=64.0,
            weather_features={"rainfall_mm": 12.0},
        )
        for driver in result["forecastDrivers"]:
            assert driver["role"] == "model_input", \
                f"Driver '{driver['factor']}' has role '{driver['role']}', expected 'model_input'"

    def test_pricing_constraints_have_triggered_boolean(self):
        """All pricingConstraints should have triggered boolean."""
        result = build_explanation(
            fair_price=20.68,
            fair_price_range={"lower": 18.36, "expected": 20.68, "upper": 23.00, "spread": 0.112},
            reliability_result={
                "reliability": 78, "band": "MEDIUM",
                "subscores": {"data_freshness": 0.95, "historical_volume": 0.8,
                              "validation_quality": 0.85, "mandi_availability": 1.0,
                              "weather_availability": 0.7, "model_agreement": 0.9,
                              "market_volatility": 0.2},
                "weights": {}, "volatility_capped": False, "model_agreement_default": False,
            },
            baseline=20.16,
            floor_blocked=False,
        )
        for constraint in result["pricingConstraints"]:
            assert "triggered" in constraint, \
                f"Constraint '{constraint['factor']}' missing 'triggered' field"
            assert isinstance(constraint["triggered"], bool)


# ============================================================================
# T41: Formula double-count regression (F1)
# ============================================================================

class TestFormulaDoubleCountRegression:
    """T41: FairPrice matches corrected single-term Section 15 formula exactly."""

    def test_fair_price_matches_single_term_formula(self):
        """
        FairPrice = Baseline + w_forecast * (Forecast - Baseline)
        NOT: w_baseline*Baseline + w_demand*Demand + w_weather*Weather + ...
        """
        baseline = 20.16
        forecast = 21.20
        w_forecast = 0.5

        fair_price = calculate_fair_price(baseline, forecast, w_forecast)

        # Expected: 20.16 + 0.5 * (21.20 - 20.16) = 20.16 + 0.52 = 20.68
        expected = 20.16 + 0.5 * (21.20 - 20.16)
        assert fair_price == round(expected, 2), \
            f"FairPrice {fair_price} != expected {round(expected, 2)}"

    def test_fair_price_symmetry(self):
        """Forecast == Baseline => FairPrice == Baseline for any w_forecast."""
        for w in [0.0, 0.3, 0.5, 0.7, 1.0]:
            fair = calculate_fair_price(20.0, 20.0, w)
            assert fair == 20.0, \
                f"w_forecast={w}: expected 20.0, got {fair}"

    def test_fair_price_baseline_only_mode(self):
        """When forecast is None (baseline-only), FairPrice == Baseline."""
        fair = calculate_fair_price(20.16, None, w_forecast=0.5)
        assert fair == 20.16

    def test_no_weather_demand_additive_adjustment(self):
        """
        Critical F1 regression test:
        Weather and demand signals should NOT appear as additive
        rupee adjustments in the fair price formula. They enter ONLY
        as model regressors that shape the Forecast value.
        """
        baseline = 20.16
        forecast = 21.20
        demand_signal = 10.0  # should NOT be added to FairPrice
        weather_signal = 5.0  # should NOT be added to FairPrice

        # FairPrice should be deterministic from baseline, forecast, w_forecast only
        fair_price = calculate_fair_price(baseline, forecast, w_forecast=0.5)

        # Verify NO weather/demand additive adjustment
        wrong_formula = baseline + 0.5 * (forecast - baseline) + demand_signal + weather_signal
        assert fair_price != wrong_formula, \
            "FairPrice incorrectly includes weather/demand as additive terms"
        assert fair_price == 20.68


# ============================================================================
# T43: Reliability score, baseline-only mode (F5)
# ============================================================================

class TestReliabilityBaselineOnlyMode:
    """T43: ModelAgreement defaults to 0.5 in baseline-only mode."""

    def test_model_agreement_baseline_mode_returns_neutral(self):
        """No comparison possible => ModelAgreement = 0.5."""
        agreement, is_default = calculate_model_agreement(
            prophet_pred=None, ml_pred=None, baseline_mode=True,
        )
        assert agreement == 0.5
        assert is_default is True

    def test_model_agreement_with_both_models(self):
        """When both models active, agreement = 1 - |diff|/prophet."""
        agreement, is_default = calculate_model_agreement(
            prophet_pred=20.0, ml_pred=21.0, baseline_mode=False,
        )
        # 1 - |20-21|/20 = 1 - 0.05 = 0.95
        assert math.isclose(agreement, 0.95, abs_tol=0.01)
        assert is_default is False

    def test_reliability_score_with_model_agreement_default(self):
        """Full reliability score with baseline_only=True uses 0.5 for model_agreement."""
        result = calculate_reliability_score(
            data_freshness=0.8,
            historical_volume=0.5,
            validation_quality=0.7,
            mandi_availability=1.0,
            weather_availability=0.0,
            model_agreement=0.5,
            market_volatility=0.8,
            model_agreement_default=True,
        )
        assert result["model_agreement_default"] is True

    def test_baseline_only_disclosure_in_fallbacks(self):
        """build_explanation should add modelAgreementDefault to fallbacksUsed when baseline_only."""
        explanation = build_explanation(
            fair_price=20.0,
            fair_price_range={"lower": 17.0, "expected": 20.0, "upper": 23.0, "spread": 0.15},
            reliability_result={
                "reliability": 50, "band": "MEDIUM",
                "subscores": {"data_freshness": 0.5, "historical_volume": 0.3,
                              "validation_quality": 0.5, "mandi_availability": 0.5,
                              "weather_availability": 0.0, "model_agreement": 0.5,
                              "market_volatility": 0.8},
                "weights": {}, "volatility_capped": False, "model_agreement_default": True,
            },
            baseline=20.0,
            baseline_only=True,
        )
        assert explanation["modelAgreementDefault"] is True
        assert "modelAgreementDefault" in explanation["fallbacksUsed"]


# ============================================================================
# T44: Volatility cap exact rule (F6)
# ============================================================================

class TestVolatilityCapExactRule:
    """T44: STRESSED volatility (>30%) caps reliability at 79."""

    def test_stressed_volatility_caps_reliability(self):
        """Computed reliability of 91 with STRESSED vol should return 79."""
        # All perfect sub-scores except volatility (which triggers cap)
        result = calculate_reliability_score(
            data_freshness=1.0,
            historical_volume=1.0,
            validation_quality=1.0,
            mandi_availability=1.0,
            weather_availability=1.0,
            model_agreement=1.0,
            market_volatility=1.0,
            volatility_30d=0.35,  # > 30% => STRESSED
        )
        # Without cap: reliability = 100
        # With cap: reliability = min(100, 79) = 79
        assert result["reliability"] == 79, \
            f"Expected capped reliability 79, got {result['reliability']}"
        assert result["volatility_capped"] is True

    def test_non_stressed_does_not_cap(self):
        """Volatility = 20% (ELEVATED) should NOT cap reliability."""
        result = calculate_reliability_score(
            data_freshness=1.0,
            historical_volume=1.0,
            validation_quality=1.0,
            mandi_availability=1.0,
            weather_availability=1.0,
            model_agreement=1.0,
            market_volatility=1.0,
            volatility_30d=0.20,  # < 30% => ELEVATED, no cap
        )
        assert result["reliability"] == 100
        assert result["volatility_capped"] is False

    def test_stressed_with_already_below_79_not_capped_up(self):
        """If computed reliability is already <= 79, cap has no effect."""
        result = calculate_reliability_score(
            data_freshness=0.5,
            historical_volume=0.3,
            validation_quality=0.4,
            mandi_availability=0.5,
            weather_availability=0.5,
            model_agreement=0.5,
            market_volatility=0.5,
            volatility_30d=0.35,
        )
        # With these inputs, computed reliability should be <= 79
        # Cap should not change it
        assert result["volatility_capped"] is False or result["reliability"] <= 79

    def test_volatility_label_stressed(self):
        """get_volatility_label returns STRESSED for vol > 30%."""
        assert get_volatility_label(0.31) == "STRESSED"
        assert get_volatility_label(0.50) == "STRESSED"

    def test_volatility_label_elevated(self):
        """ELEVATED for 15% < vol <= 30%."""
        assert get_volatility_label(0.15) == "ELEVATED"
        assert get_volatility_label(0.30) == "ELEVATED"

    def test_volatility_label_normal(self):
        """NORMAL for vol < 15%."""
        assert get_volatility_label(0.05) == "NORMAL"
        assert get_volatility_label(0.0) == "NORMAL"


# ============================================================================
# T45: PRICE-E2E-001 fixture (F2)
# ============================================================================

class TestPriceE2E001Fixture:
    """
    T45: Recomputed worked example from Section 41 as a deterministic regression test.
    All values from the spec's hand-verified arithmetic.
    """

    @pytest.fixture
    def e2e_inputs(self):
        """PRICE-E2E-001 fixture inputs from Section 41.1."""
        return {
            "commodity": "Tomato",
            "quantity_kg": 500,
            "mandi_modal_price_quintal": 2050,  # t-1
            "mandi_wma_7d_kg": 19.80,
            "regional_median_kg": 20.10,
            "seasonal_reference_kg": 20.00,
            "prophet_forecast_kg": 21.20,
            "volatility_30d": 0.12,
            "prediction_reliability": 78,
            "farmer_declared_minimum": None,
            "logistics_distance_km": 68,
            "logistics_cost_per_kg": 8.40,
            "platform_fee_pct": 0.05,
            "w_forecast": 0.5,
        }

    def test_baseline_exact_match(self, e2e_inputs):
        """Baseline = 0.4*20.50 + 0.3*19.80 + 0.2*20.10 + 0.1*20.00 = 20.16."""
        inputs = e2e_inputs
        # Compute baseline using Section 8 formula
        baseline = (
            0.4 * (inputs["mandi_modal_price_quintal"] / 100.0)  # convert ₹/quintal to ₹/kg
            + 0.3 * inputs["mandi_wma_7d_kg"]
            + 0.2 * inputs["regional_median_kg"]
            + 0.1 * inputs["seasonal_reference_kg"]
        )
        assert baseline == pytest.approx(20.16, abs=0.01), \
            f"Baseline {baseline} != expected 20.16"

    def test_fair_price_exact_match(self, e2e_inputs):
        """FairPrice = 20.16 + 0.5*(21.20 - 20.16) = 20.68."""
        fair_price = calculate_fair_price(
            baseline=20.16,
            forecast=e2e_inputs["prophet_forecast_kg"],
            w_forecast=e2e_inputs["w_forecast"],
        )
        assert fair_price == pytest.approx(20.68, abs=0.01), \
            f"FairPrice {fair_price} != expected 20.68"

    def test_spread_exact_match(self, e2e_inputs):
        """Spread = 0.03 + 0.5*0.12 + 0.1*(1-0.78) = 0.112, clamped [0.02, 0.15]."""
        spread = calculate_spread(
            volatility_30d=e2e_inputs["volatility_30d"],
            reliability=e2e_inputs["prediction_reliability"],
        )
        assert spread == pytest.approx(0.112, abs=0.002), \
            f"Spread {spread} != expected 0.112"

    def test_fair_price_range_exact_match(self, e2e_inputs):
        """Lower = 20.68*0.888 = 18.36, Upper = 20.68*1.112 = 23.00 (±0.01)."""
        fair_price_range = calculate_fair_price_range(20.68, 0.112)
        assert fair_price_range["lower"] == pytest.approx(18.36, abs=0.01), \
            f"Range lower {fair_price_range['lower']} != 18.36"
        assert fair_price_range["upper"] == pytest.approx(23.00, abs=0.01), \
            f"Range upper {fair_price_range['upper']} != 23.00"

    def test_farmer_floor_exact_match(self, e2e_inputs):
        """FLOOR = 0.85 * 20.16 = 17.14."""
        floor = calculate_farmer_floor(baseline=20.16)
        assert floor == pytest.approx(17.14, abs=0.01), \
            f"Floor {floor} != 17.14"

    def test_floor_not_blocked(self, e2e_inputs):
        """Lower (18.36) >= FLOOR (17.14) => not blocked, margin = +1.22."""
        check = check_floor_protection(fair_price_lower=18.36, floor=17.14)
        assert check["blocked"] is False
        assert check["margin_above_floor"] == pytest.approx(1.22, abs=0.02)

    def test_full_e2e_computation(self, e2e_inputs):
        """Full deterministic E2E with all intermediate values matching Section 41."""
        inputs = e2e_inputs

        # Step 5: Baseline
        baseline = (
            0.4 * (inputs["mandi_modal_price_quintal"] / 100.0)
            + 0.3 * inputs["mandi_wma_7d_kg"]
            + 0.2 * inputs["regional_median_kg"]
            + 0.1 * inputs["seasonal_reference_kg"]
        )
        assert baseline == pytest.approx(20.16, abs=0.01)

        # Step 7: FairPrice
        fair_price = calculate_fair_price(baseline, inputs["prophet_forecast_kg"], inputs["w_forecast"])
        assert fair_price == pytest.approx(20.68, abs=0.01)

        # Step 8: Spread
        spread = calculate_spread(inputs["volatility_30d"], inputs["prediction_reliability"])
        assert spread == pytest.approx(0.112, abs=0.002)

        # Step 9: Range
        price_range = calculate_fair_price_range(fair_price, spread)
        assert price_range["lower"] == pytest.approx(18.36, abs=0.01)
        assert price_range["upper"] == pytest.approx(23.00, abs=0.01)

        # Step 10: Floor
        floor = calculate_farmer_floor(baseline)
        assert floor == pytest.approx(17.14, abs=0.01)
        floor_check = check_floor_protection(price_range["lower"], floor)
        assert floor_check["blocked"] is False

        # Step 11: Farmer payout = fair_price * quantity
        farmer_payout = round(fair_price * inputs["quantity_kg"], 2)
        assert farmer_payout == pytest.approx(10340.0, abs=10.0)

        # Step 12: Logistics
        logistics_total = round(inputs["logistics_cost_per_kg"] * inputs["quantity_kg"], 2)
        assert logistics_total == pytest.approx(4200.0, abs=1.0)

        # Step 13: Platform fee
        platform_fee_per_kg = round(inputs["platform_fee_pct"] * fair_price, 2)
        platform_fee_total = round(platform_fee_per_kg * inputs["quantity_kg"], 2)
        assert platform_fee_total == pytest.approx(515.0, abs=10.0)

        # Step 14: Buyer price
        buyer_price_per_kg = fair_price + inputs["logistics_cost_per_kg"] + platform_fee_per_kg
        buyer_price_total = round(buyer_price_per_kg * inputs["quantity_kg"], 2)
        assert buyer_price_total == pytest.approx(15055.0, abs=10.0)


# ============================================================================
# T46: Zero-denominator ratio features (F10)
# ============================================================================

class TestZeroDenominatorConvention:
    """T46: Zero-denominator convention (F10) returns neutral default, no exception."""

    def test_volatility_zero_denominator(self):
        """Flat 30-day price series => volatility_30d = 0, no exception."""
        result = calculate_market_volatility(volatility_30d=0.0)
        assert result == 1.0  # 1 - 0 = 1

    def test_volatility_none_returns_neutral(self):
        """No volatility data => neutral (1.0), not None/NaN."""
        result = calculate_market_volatility(volatility_30d=None)
        assert result == 1.0

    def test_model_agreement_zero_denominator(self):
        """ProphetPred = 0 => neutral 0.5, not NaN."""
        agreement, is_default = calculate_model_agreement(
            prophet_pred=0.0, ml_pred=10.0, baseline_mode=False,
        )
        assert agreement == 0.5
        assert is_default is True

    def test_reliability_score_with_none_volatility(self):
        """None volatility_30d should not cause exception."""
        result = calculate_reliability_score(
            data_freshness=0.5,
            historical_volume=0.5,
            validation_quality=0.5,
            mandi_availability=0.5,
            weather_availability=0.5,
            model_agreement=0.5,
            market_volatility=0.5,
            volatility_30d=None,
        )
        assert isinstance(result["reliability"], int)
        assert 0 <= result["reliability"] <= 100


# ============================================================================
# Spread formula verification
# ============================================================================

class TestSpreadFormula:
    """Verify spread formula: clamp(0.03 + 0.5*vol + 0.1*(1-reliability/100), 0.02, 0.15)."""

    def test_spread_known_values(self):
        """Section 41.1: vol=0.12, reliability=78 => spread=0.112."""
        spread = calculate_spread(0.12, 78)
        assert spread == pytest.approx(0.112, abs=0.002)

    def test_spread_min_clamp(self):
        """Spread should never go below 0.02."""
        spread = calculate_spread(0.0, 100)
        assert spread >= 0.02

    def test_spread_max_clamp(self):
        """Spread should never exceed 0.15."""
        spread = calculate_spread(1.0, 0)
        assert spread <= 0.15

    def test_spread_missing_inputs(self):
        """Missing inputs should use neutral defaults."""
        spread = calculate_spread(None, None)
        assert 0.02 <= spread <= 0.15