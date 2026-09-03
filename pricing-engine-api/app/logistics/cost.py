"""
Logistics cost calculation - Section 18.

Formulas:
    PickupCost = distance_km × per_km_rate × trips
    HandlingCost = (loading_fee + unloading_fee) × trips
    TotalLogistics = PickupCost + HandlingCost
    CostPerKg = TotalLogistics / quantity_kg
    BuyerPrice = FarmerPayout + CostPerKg + PlatformFee

Units:
    distance → km
    quantity → kg
    cost → ₹
"""
import math
from typing import Optional, Dict, Any


def calculate_required_trips(
    quantity_kg: float,
    vehicle_capacity_kg: float,
) -> int:
    """
    Calculate number of trips needed.

    Args:
        quantity_kg: Total shipment quantity in kg
        vehicle_capacity_kg: Vehicle capacity in kg

    Returns:
        Number of trips (ceil division)

    Raises:
        ValueError: If quantity or capacity invalid
    """
    if quantity_kg <= 0:
        raise ValueError(f"quantity_kg must be > 0, got {quantity_kg}")
    if vehicle_capacity_kg <= 0:
        raise ValueError(f"vehicle_capacity_kg must be > 0, got {vehicle_capacity_kg}")

    return math.ceil(quantity_kg / vehicle_capacity_kg)


def calculate_logistics_cost(
    distance_km: float,
    quantity_kg: float,
    vehicle_capacity_kg: float,
    cost_per_km: float,
    handling_cost_per_point: float = 30.0,
    spoilage_buffer_per_kg: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate full logistics cost breakdown.

    Args:
        distance_km: Trip distance in kilometers
        quantity_kg: Shipment quantity in kilograms
        vehicle_capacity_kg: Vehicle capacity in kilograms
        cost_per_km: Transportation rate in ₹ per km
        handling_cost_per_point: Handling cost per loading/unloading point (₹)
        spoilage_buffer_per_kg: Spoilage buffer per kg (₹/kg), 0 if disabled

    Returns:
        Dictionary with cost breakdown and per-kg cost

    Raises:
        ValueError: If any input is invalid (negative, zero, non-numeric, NaN/inf)
    """
    # Validate all inputs
    for name, val in [
        ("distance_km", distance_km),
        ("quantity_kg", quantity_kg),
        ("vehicle_capacity_kg", vehicle_capacity_kg),
        ("cost_per_km", cost_per_km),
        ("handling_cost_per_point", handling_cost_per_point),
        ("spoilage_buffer_per_kg", spoilage_buffer_per_kg),
    ]:
        if not isinstance(val, (int, float)):
            raise ValueError(f"{name} must be numeric, got {type(val).__name__}")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"{name} must be finite, got {val}")
        if "cost_per_km" in name and val < 0:
            raise ValueError(f"{name} must be >= 0, got {val}")

    if distance_km < 0:
        raise ValueError(f"distance_km must be >= 0, got {distance_km}")
    if quantity_kg <= 0:
        raise ValueError(f"quantity_kg must be > 0, got {quantity_kg}")
    if vehicle_capacity_kg <= 0:
        raise ValueError(f"vehicle_capacity_kg must be > 0, got {vehicle_capacity_kg}")

    # Calculate trips
    trips = calculate_required_trips(quantity_kg, vehicle_capacity_kg)

    # Transportation cost (distance × rate × trips)
    transport_cost = distance_km * cost_per_km * trips

    # Handling cost (loading + unloading)
    handling_cost = handling_cost_per_point * 2 * trips

    # Spoilage buffer (per kg, if enabled)
    spoilage_buffer = spoilage_buffer_per_kg * quantity_kg

    # Total logistics
    total_cost = transport_cost + handling_cost + spoilage_buffer

    # Per-kg cost
    cost_per_kg = total_cost / quantity_kg

    return {
        "distance_km": round(distance_km, 2),
        "quantity_kg": round(quantity_kg, 2),
        "vehicle_capacity_kg": vehicle_capacity_kg,
        "trips": trips,
        "transport_cost": round(transport_cost, 2),
        "handling_cost": round(handling_cost, 2),
        "spoilage_buffer": round(spoilage_buffer, 2),
        "total_logistics_cost": round(total_cost, 2),
        "cost_per_kg": round(cost_per_kg, 2),
    }


def calculate_buyer_price(
    farmer_payout_per_kg: float,
    logistics_cost_per_kg: float,
    platform_fee_pct: float = 0.05,
) -> Dict[str, Any]:
    """
    Calculate final buyer price.

    BuyerPrice = FarmerPayout + LogisticsCostPerKg + PlatformFeePerKg
    PlatformFeePerKg = FarmerPayout × platform_fee_pct

    Args:
        farmer_payout_per_kg: Fair price in ₹/kg
        logistics_cost_per_kg: Logistics cost per kg (₹/kg)
        platform_fee_pct: Platform fee as fraction of payout (default 0.05)

    Returns:
        Dictionary with price breakdown
    """
    if farmer_payout_per_kg < 0 or logistics_cost_per_kg < 0:
        raise ValueError("Prices must be non-negative")
    if platform_fee_pct < 0:
        raise ValueError("Platform fee percentage must be >= 0")

    platform_fee_per_kg = farmer_payout_per_kg * platform_fee_pct
    buyer_price_per_kg = farmer_payout_per_kg + logistics_cost_per_kg + platform_fee_per_kg

    return {
        "farmer_payout_per_kg": round(farmer_payout_per_kg, 2),
        "logistics_cost_per_kg": round(logistics_cost_per_kg, 2),
        "platform_fee_per_kg": round(platform_fee_per_kg, 2),
        "buyer_price_per_kg": round(buyer_price_per_kg, 2),
    }