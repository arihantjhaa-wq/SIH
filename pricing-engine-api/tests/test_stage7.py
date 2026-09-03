"""
Stage 7 Test Suite: Logistics Calculation Layer

Tests T18-T23 from spec Section 31.

T18: Logistics cost formula
T19: Vehicle class selection
T20: Pooling capacity split (deferred to V0.2, simplified tests)
T21: Pooling cost allocation (deferred to V0.2, simplified tests)
T22: Spoilage score bounds
T23: Final price formula

Additional logistics-specific tests:
- Distance calculation (Haversine)
- Input validation
- Trip calculation
- Configuration loading
- Integration with pricing engine
"""
import math
import pytest
from typing import Dict, Any

from app.logistics.distance import (
    calculate_distance_km,
    calculate_distance_with_road_factor,
)
from app.logistics.cost import (
    calculate_logistics_cost,
    calculate_buyer_price,
    calculate_required_trips,
)
from app.logistics.validate import (
    validate_logistics_inputs,
    validate_coordinates,
    LogisticsValidationError,
)
from app.logistics.engine import (
    estimate_logistics,
    estimate_logistics_with_pricing,
    select_vehicle_class,
    _load_logistics_config,
)


# ============================================================================
# Helper fixtures
# ============================================================================

@pytest.fixture
def sample_locations():
    """Known test locations in Maharashtra, India."""
    # Pune and Mumbai coordinates
    return {
        "pune_lat": 18.5204,
        "pune_lon": 73.8567,
        "mumbai_lat": 19.0760,
        "mumbai_lon": 72.8777,
        # Expected distance ~120km by road (Haversine ~118km × 1.3)
    }


@pytest.fixture
def sample_vehicle_config():
    """Sample vehicle configuration."""
    return {
        "vehicle_capacity_kg": 1000.0,
        "cost_per_km": 12.0,
        "handling_cost_per_point": 30.0,
        "spoilage_buffer_per_kg": 0.0,
    }


@pytest.fixture
def sample_logistics_inputs(sample_locations):
    """Sample inputs for full logistics estimation."""
    return {
        "farmer_lat": sample_locations["pune_lat"],
        "farmer_lon": sample_locations["pune_lon"],
        "buyer_lat": sample_locations["mumbai_lat"],
        "buyer_lon": sample_locations["mumbai_lon"],
        "quantity_kg": 500.0,
    }


# ============================================================================
# Distance calculation tests
# ============================================================================

class TestDistanceCalculation:
    """Distance calculation using Haversine formula."""

    def test_same_location_returns_zero(self):
        """Same coordinates should return 0 km."""
        distance = calculate_distance_km(18.5204, 73.8567, 18.5204, 73.8567)
        assert distance == 0.0

    def test_known_distance_pune_mumbai(self, sample_locations):
        """Pune to Mumbai should be approximately 118 km straight-line."""
        distance = calculate_distance_km(
            sample_locations["pune_lat"],
            sample_locations["pune_lon"],
            sample_locations["mumbai_lat"],
            sample_locations["mumbai_lon"],
        )
        # Actual Haversine distance ~118 km
        assert 115 < distance < 125, f"Expected ~118km, got {distance}"

    def test_with_road_factor(self, sample_locations):
        """Road distance should be straight-line × 1.3."""
        straight_line = calculate_distance_km(
            sample_locations["pune_lat"],
            sample_locations["pune_lon"],
            sample_locations["mumbai_lat"],
            sample_locations["mumbai_lon"],
        )
        road_distance = calculate_distance_with_road_factor(
            sample_locations["pune_lat"],
            sample_locations["pune_lon"],
            sample_locations["mumbai_lat"],
            sample_locations["mumbai_lon"],
            road_factor=1.3,
        )
        assert road_distance == pytest.approx(straight_line * 1.3, rel=0.001)

    def test_invalid_latitude_raises_error(self):
        """Latitude > 90 should raise ValueError."""
        with pytest.raises(ValueError, match="Latitude must be between"):
            calculate_distance_km(999, 0, 0, 0)

    def test_invalid_longitude_raises_error(self):
        """Longitude > 180 should raise ValueError."""
        with pytest.raises(ValueError, match="Longitude must be between"):
            calculate_distance_km(0, 999, 0, 0)

    def test_non_numeric_coordinates_raise_error(self):
        """Non-numeric coordinates should raise ValueError."""
        with pytest.raises(ValueError, match="Coordinates must be numeric"):
            calculate_distance_km("invalid", 0, 0, 0)


# ============================================================================
# Trip calculation tests
# ============================================================================

class TestTripCalculation:
    """Calculate required trips based on quantity and capacity."""

    def test_small_quantity_one_trip(self):
        """Quantity < capacity should require 1 trip."""
        trips = calculate_required_trips(500, 1000)
        assert trips == 1

    def test_exact_capacity_one_trip(self):
        """Quantity == capacity should require 1 trip."""
        trips = calculate_required_trips(1000, 1000)
        assert trips == 1

    def test_large_quantity_multiple_trips(self):
        """Quantity > capacity should require multiple trips."""
        trips = calculate_required_trips(2500, 1000)
        assert trips == 3  # ceil(2500/1000)

    def test_very_large_quantity(self):
        """Large quantity should calculate correctly."""
        trips = calculate_required_trips(10000, 1000)
        assert trips == 10

    def test_zero_quantity_raises_error(self):
        """Quantity <= 0 should raise ValueError."""
        with pytest.raises(ValueError, match="quantity_kg must be > 0"):
            calculate_required_trips(0, 1000)

    def test_negative_quantity_raises_error(self):
        """Negative quantity should raise ValueError."""
        with pytest.raises(ValueError, match="quantity_kg must be > 0"):
            calculate_required_trips(-100, 1000)

    def test_zero_capacity_raises_error(self):
        """Vehicle capacity <= 0 should raise ValueError."""
        with pytest.raises(ValueError, match="vehicle_capacity_kg must be > 0"):
            calculate_required_trips(1000, 0)

    def test_negative_capacity_raises_error(self):
        """Negative capacity should raise ValueError."""
        with pytest.raises(ValueError, match="vehicle_capacity_kg must be > 0"):
            calculate_required_trips(1000, -100)


# ============================================================================
# Logistics cost formula tests (T18)
# ============================================================================

class TestLogisticsCostFormula:
    """T18: Verify logistics cost matches formula."""

    def test_cost_formula_with_known_inputs(self):
        """
        TransportCost = distance × rate × trips
        HandlingCost = handling_per_point × 2 × trips
        Total = TransportCost + HandlingCost
        CostPerKg = Total / quantity
        """
        distance = 68.0  # km
        quantity = 500.0  # kg
        capacity = 1000.0  # kg
        cost_per_km = 12.0  # ₹/km
        handling = 30.0  # ₹/point

        result = calculate_logistics_cost(
            distance_km=distance,
            quantity_kg=quantity,
            vehicle_capacity_kg=capacity,
            cost_per_km=cost_per_km,
            handling_cost_per_point=handling,
            spoilage_buffer_per_kg=0.0,
        )

        # Expected calculations
        trips = 1  # ceil(500/1000)
        transport_cost = 68.0 * 12.0 * 1  # 816
        handling_cost = 30.0 * 2 * 1  # 60
        total = 816 + 60  # 876
        cost_per_kg = 876 / 500  # 1.752

        assert result["trips"] == trips
        assert result["transport_cost"] == pytest.approx(816.0, rel=0.01)
        assert result["handling_cost"] == pytest.approx(60.0, rel=0.01)
        assert result["total_logistics_cost"] == pytest.approx(876.0, rel=0.01)
        assert result["cost_per_kg"] == pytest.approx(1.752, rel=0.01)

    def test_cost_with_multiple_trips(self):
        """Quantity > capacity should increase trips and costs."""
        result = calculate_logistics_cost(
            distance_km=50.0,
            quantity_kg=2500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
            handling_cost_per_point=20.0,
        )

        # trips = ceil(2500/1000) = 3
        assert result["trips"] == 3
        # transport = 50 × 10 × 3 = 1500
        assert result["transport_cost"] == 1500.0
        # handling = 20 × 2 × 3 = 120
        assert result["handling_cost"] == 120.0

    def test_zero_handling_cost(self):
        """Zero handling cost should work correctly."""
        result = calculate_logistics_cost(
            distance_km=100.0,
            quantity_kg=1000.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
            handling_cost_per_point=0.0,
        )
        assert result["handling_cost"] == 0.0
        # transport = 100 × 10 × 1 = 1000
        assert result["transport_cost"] == 1000.0
        assert result["total_logistics_cost"] == 1000.0

    def test_cost_per_kg_calculation(self):
        """Cost per kg should equal total / quantity."""
        result = calculate_logistics_cost(
            distance_km=60.0,
            quantity_kg=200.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=15.0,
            handling_cost_per_point=50.0,
            spoilage_buffer_per_kg=0.5,
        )

        expected_total = (
            60 * 15 * 1 +  # transport
            50 * 2 * 1 +   # handling
            0.5 * 200       # spoilage
        )
        assert result["total_logistics_cost"] == pytest.approx(expected_total, rel=0.01)
        assert result["cost_per_kg"] == pytest.approx(expected_total / 200, rel=0.01)

    def test_negative_distance_raises_error(self):
        """Negative distance should raise ValueError."""
        with pytest.raises(ValueError, match="distance_km must be >= 0"):
            calculate_logistics_cost(
                distance_km=-10.0,
                quantity_kg=100.0,
                vehicle_capacity_kg=1000.0,
                cost_per_km=10.0,
            )

    def test_zero_quantity_raises_error(self):
        """Zero quantity should raise ValueError."""
        with pytest.raises(ValueError, match="quantity_kg must be > 0"):
            calculate_logistics_cost(
                distance_km=10.0,
                quantity_kg=0.0,
                vehicle_capacity_kg=1000.0,
                cost_per_km=10.0,
            )

    def test_nan_distance_raises_error(self):
        """NaN distance should raise ValueError."""
        with pytest.raises(ValueError, match="must be finite"):
            calculate_logistics_cost(
                distance_km=float("nan"),
                quantity_kg=100.0,
                vehicle_capacity_kg=1000.0,
                cost_per_km=10.0,
            )

    def test_infinite_cost_raises_error(self):
        """Infinite cost per km should raise ValueError."""
        with pytest.raises(ValueError, match="must be finite"):
            calculate_logistics_cost(
                distance_km=10.0,
                quantity_kg=100.0,
                vehicle_capacity_kg=1000.0,
                cost_per_km=float("inf"),
            )


# ============================================================================
# Vehicle class selection tests (T19)
# ============================================================================

class TestVehicleClassSelection:
    """T19: Select appropriate vehicle class for quantity."""

    def test_small_quantity_selects_smallest_vehicle(self):
        """Quantity < 200kg should select auto_rickshaw."""
        vehicle = select_vehicle_class(150)
        assert vehicle["name"] == "auto_rickshaw"
        assert vehicle["capacity_kg"] == 200

    def test_medium_quantity_selects_tempo(self):
        """Quantity ~500kg should select tempo."""
        vehicle = select_vehicle_class(500)
        assert vehicle["name"] == "tempo"
        assert vehicle["capacity_kg"] == 1000

    def test_large_quantity_selects_mini_truck(self):
        """Quantity ~2000kg should select mini_truck."""
        vehicle = select_vehicle_class(2000)
        assert vehicle["name"] == "mini_truck"
        assert vehicle["capacity_kg"] == 2500

    def test_very_large_quantity_selects_truck(self):
        """Quantity > 2500kg should select truck."""
        vehicle = select_vehicle_class(3000)
        assert vehicle["name"] == "truck"
        assert vehicle["capacity_kg"] == 5000

    def test_exact_capacity_match(self):
        """Quantity exactly at capacity should select that vehicle."""
        vehicle = select_vehicle_class(1000)
        assert vehicle["capacity_kg"] == 1000
        assert vehicle["name"] == "tempo"


# ============================================================================
# Input validation tests
# ============================================================================

class TestInputValidation:
    """Validate logistics inputs."""

    def test_valid_inputs_no_errors(self, sample_locations, sample_logistics_inputs):
        """Valid inputs should return empty error list."""
        errors = validate_logistics_inputs(
            farmer_lat=sample_logistics_inputs["farmer_lat"],
            farmer_lon=sample_logistics_inputs["farmer_lon"],
            buyer_lat=sample_logistics_inputs["buyer_lat"],
            buyer_lon=sample_logistics_inputs["buyer_lon"],
            quantity_kg=500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=12.0,
        )
        assert len(errors) == 0

    def test_missing_farmer_latitude(self):
        """Missing farmer lat should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=None, farmer_lon=73.0,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=500.0, vehicle_capacity_kg=1000.0, cost_per_km=12.0,
        )
        assert len(errors) == 1
        assert "farmer_location" in errors[0].field

    def test_missing_buyer_longitude(self):
        """Missing buyer lon should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=18.0, farmer_lon=73.0,
            buyer_lat=19.0, buyer_lon=None,
            quantity_kg=500.0, vehicle_capacity_kg=1000.0, cost_per_km=12.0,
        )
        assert len(errors) == 1
        assert "buyer_location" in errors[0].field

    def test_invalid_latitude(self):
        """Latitude > 90 should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=999, farmer_lon=73.0,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=500.0, vehicle_capacity_kg=1000.0, cost_per_km=12.0,
        )
        assert len(errors) == 1
        assert "Latitude" in errors[0].message

    def test_invalid_longitude(self):
        """Longitude > 180 should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=18.0, farmer_lon=999,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=500.0, vehicle_capacity_kg=1000.0, cost_per_km=12.0,
        )
        assert len(errors) == 1
        assert "Longitude" in errors[0].message

    def test_zero_quantity(self):
        """Zero quantity should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=18.0, farmer_lon=73.0,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=0.0, vehicle_capacity_kg=1000.0, cost_per_km=12.0,
        )
        assert len(errors) == 1
        assert "quantity_kg" in errors[0].field

    def test_negative_quantity(self):
        """Negative quantity should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=18.0, farmer_lon=73.0,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=-100.0, vehicle_capacity_kg=1000.0, cost_per_km=12.0,
        )
        assert len(errors) == 1
        assert "quantity_kg" in errors[0].field

    def test_zero_capacity(self):
        """Zero capacity should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=18.0, farmer_lon=73.0,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=500.0, vehicle_capacity_kg=0.0, cost_per_km=12.0,
        )
        assert len(errors) == 1
        assert "vehicle_capacity_kg" in errors[0].field

    def test_negative_cost_per_km(self):
        """Negative cost per km should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=18.0, farmer_lon=73.0,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=500.0, vehicle_capacity_kg=1000.0, cost_per_km=-10.0,
        )
        assert len(errors) == 1
        assert "cost_per_km" in errors[0].field

    def test_nan_quantity(self):
        """NaN quantity should return error."""
        errors = validate_logistics_inputs(
            farmer_lat=18.0, farmer_lon=73.0,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=float("nan"), vehicle_capacity_kg=1000.0, cost_per_km=12.0,
        )
        assert len(errors) == 1
        assert "quantity_kg" in errors[0].field

    def test_multiple_errors(self):
        """Multiple invalid inputs should return multiple errors."""
        errors = validate_logistics_inputs(
            farmer_lat=None, farmer_lon=None,
            buyer_lat=999, buyer_lon=999,
            quantity_kg=-100.0, vehicle_capacity_kg=0.0, cost_per_km=-5.0,
        )
        assert len(errors) > 1


# ============================================================================
# Full logistics estimation tests
# ============================================================================

class TestLogisticsEstimation:
    """Test the full logistics estimation pipeline."""

    def test_estimation_with_valid_inputs(self, sample_logistics_inputs):
        """Valid inputs should produce complete logistics result."""
        result = estimate_logistics(**sample_logistics_inputs)

        assert "distance_km" in result
        assert "cost_per_kg" in result
        assert "total_logistics_cost" in result
        assert "breakdown" in result
        assert "is_fallback" in result
        assert result["is_fallback"] is False

    def test_estimation_auto_selects_vehicle(self, sample_logistics_inputs):
        """Should auto-select vehicle when not provided."""
        result = estimate_logistics(**sample_logistics_inputs)
        # 500kg should get tempo (1000kg capacity)
        assert result["vehicle_capacity_kg"] == 1000
        assert result["trips"] == 1

    def test_estimation_with_fallback_distance(self):
        """Missing coordinates should use fallback distance."""
        result = estimate_logistics(
            farmer_lat=None, farmer_lon=None,
            buyer_lat=19.0, buyer_lon=72.0,
            quantity_kg=500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=12.0,
            fallback_distance_km=50.0,
        )
        assert result["is_fallback"] is True
        assert result["distance_km"] == 50.0

    def test_estimation_no_fallback_raises_error(self):
        """Missing coordinates without fallback should raise error."""
        with pytest.raises(LogisticsValidationError):
            estimate_logistics(
                farmer_lat=None, farmer_lon=None,
                buyer_lat=19.0, buyer_lon=72.0,
                quantity_kg=500.0,
            )

    def test_estimation_with_spoilage_buffer(self, sample_logistics_inputs):
        """Spoilage buffer should be included in total."""
        result_without = estimate_logistics(**sample_logistics_inputs)
        result_with = estimate_logistics(
            **sample_logistics_inputs,
            spoilage_buffer_per_kg=0.5,
        )
        assert result_with["spoilage_buffer"] > 0
        assert result_with["total_logistics_cost"] > result_without["total_logistics_cost"]


# ============================================================================
# Buyer price calculation tests (T23)
# ============================================================================

class TestBuyerPriceFormula:
    """T23: Verify final price formula."""

    def test_buyer_price_formula(self):
        """BuyerPrice = FarmerPayout + Logistics + PlatformFee."""
        result = calculate_buyer_price(
            farmer_payout_per_kg=20.0,
            logistics_cost_per_kg=2.0,
            platform_fee_pct=0.05,
        )

        # Platform fee = 20.0 × 0.05 = 1.0
        # Buyer price = 20.0 + 2.0 + 1.0 = 23.0
        assert result["platform_fee_per_kg"] == pytest.approx(1.0, rel=0.01)
        assert result["buyer_price_per_kg"] == pytest.approx(23.0, rel=0.01)

    def test_buyer_price_zero_logistics(self):
        """Zero logistics should still calculate correctly."""
        result = calculate_buyer_price(
            farmer_payout_per_kg=15.0,
            logistics_cost_per_kg=0.0,
            platform_fee_pct=0.05,
        )
        # Platform fee = 0.75, buyer price = 15.75
        assert result["buyer_price_per_kg"] == pytest.approx(15.75, rel=0.01)

    def test_buyer_price_zero_platform_fee(self):
        """Zero platform fee should work correctly."""
        result = calculate_buyer_price(
            farmer_payout_per_kg=25.0,
            logistics_cost_per_kg=3.0,
            platform_fee_pct=0.0,
        )
        # Buyer price = 25.0 + 3.0 + 0.0 = 28.0
        assert result["buyer_price_per_kg"] == pytest.approx(28.0, rel=0.01)


# ============================================================================
# Integration with pricing tests
# ============================================================================

class TestPricingIntegration:
    """Integration test with pricing result."""

    def test_integration_with_pricing_result(self, sample_logistics_inputs):
        """Full integration: pricing + logistics → buyer price."""
        # Mock pricing result
        pricing_result = {
            "fair_price": 20.68,
            "baseline": 20.16,
            "status": "OK",
        }

        # Get logistics estimate
        logistics_result = estimate_logistics(**sample_logistics_inputs)

        # Combine
        combined = estimate_logistics_with_pricing(pricing_result, logistics_result)

        assert "buyer_price_per_kg" in combined
        assert "logistics_cost_per_kg" in combined
        assert "platform_fee_per_kg" in combined
        assert combined["buyer_price_per_kg"] > combined["fair_price"]

    def test_integration_price_e2e_001(self):
        """
        PRICE-E2E-001 fixture verification.
        Crop: Tomato, Qty: 500 kg
        FairPrice: ₹20.68/kg
        Logistics: ₹8.40/kg
        Platform: ₹1.03/kg
        BuyerPrice: ₹30.11/kg
        """
        pricing_result = {
            "fair_price": 20.68,
            "baseline": 20.16,
        }

        logistics_result = {
            "distance_km": 68.0,
            "quantity_kg": 500.0,
            "vehicle_capacity_kg": 1000.0,
            "cost_per_kg": 8.40,
            "total_logistics_cost": 4200.0,
        }

        combined = estimate_logistics_with_pricing(
            pricing_result,
            logistics_result,
            platform_fee_pct=0.05,
        )

        # Platform fee = 20.68 × 0.05 = 1.034
        assert combined["platform_fee_per_kg"] == pytest.approx(1.034, abs=0.02)
        # Buyer price = 20.68 + 8.40 + 1.034 = 30.114
        assert combined["buyer_price_per_kg"] == pytest.approx(30.114, abs=0.02)
        # Total buyer price = 30.114 × 500 = 15057
        assert combined["buyer_price_total"] == pytest.approx(15057.0, abs=20.0)


# ============================================================================
# Configuration loading tests
# ============================================================================

class TestConfiguration:
    """Test configuration loading and defaults."""

    def test_load_config_returns_dict(self):
        """Config loader should return dictionary."""
        config = _load_logistics_config()
        assert isinstance(config, dict)
        assert "vehicle_classes" in config

    def test_config_has_vehicle_classes(self):
        """Config should have at least one vehicle class."""
        config = _load_logistics_config()
        assert len(config["vehicle_classes"]) > 0

    def test_config_vehicle_classes_sorted_by_capacity(self):
        """Vehicle classes should be sorted by capacity."""
        config = _load_logistics_config()
        capacities = [v["capacity_kg"] for v in config["vehicle_classes"]]
        assert capacities == sorted(capacities)


# ============================================================================
# Spoilage bounds tests (T22)
# ============================================================================

class TestSpoilageBounds:
    """T22: Spoilage score should be bounded [0, 100]."""

    def test_spoilage_with_zero_buffer(self):
        """Zero buffer should give zero spoilage cost."""
        result = calculate_logistics_cost(
            distance_km=100.0,
            quantity_kg=500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
            spoilage_buffer_per_kg=0.0,
        )
        assert result["spoilage_buffer"] == 0.0

    def test_spoilage_with_buffer(self):
        """Positive buffer should increase total cost."""
        result = calculate_logistics_cost(
            distance_km=100.0,
            quantity_kg=500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
            spoilage_buffer_per_kg=0.5,
        )
        assert result["spoilage_buffer"] == 250.0  # 0.5 × 500


# ============================================================================
# Edge case tests
# ============================================================================

class TestEdgeCases:
    """Edge case handling for logistics calculations."""

    def test_large_quantity(self):
        """Large quantity should calculate correctly."""
        result = calculate_logistics_cost(
            distance_km=50.0,
            quantity_kg=10000.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
            handling_cost_per_point=20.0,
        )
        # trips = ceil(10000/1000) = 10
        assert result["trips"] == 10

    def test_very_small_quantity(self):
        """Very small quantity should require 1 trip."""
        result = calculate_logistics_cost(
            distance_km=10.0,
            quantity_kg=1.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
            handling_cost_per_point=30.0,
        )
        assert result["trips"] == 1

    def test_zero_distance(self):
        """Zero distance should have zero transport cost."""
        result = calculate_logistics_cost(
            distance_km=0.0,
            quantity_kg=500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
            handling_cost_per_point=30.0,
        )
        assert result["transport_cost"] == 0.0
        assert result["handling_cost"] == 60.0  # 30 × 2 × 1
        assert result["total_logistics_cost"] == 60.0

    def test_exact_division(self):
        """Quantity exactly divisible by capacity."""
        result = calculate_logistics_cost(
            distance_km=100.0,
            quantity_kg=2000.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
        )
        assert result["trips"] == 2

    def test_non_exact_division(self):
        """Quantity not exactly divisible by capacity."""
        result = calculate_logistics_cost(
            distance_km=100.0,
            quantity_kg=1500.0,
            vehicle_capacity_kg=1000.0,
            cost_per_km=10.0,
        )
        assert result["trips"] == 2  # ceil(1.5) = 2
