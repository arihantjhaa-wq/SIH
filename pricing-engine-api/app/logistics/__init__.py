"""
Logistics module - MVP Logistics Calculation Layer (Stage 7).

Distance (Haversine) → Logistics Cost → Cost per kg → Buyer Price.

Formulas (Section 18, simplified for MVP):
    Distance = Haversine(lat1,lon1, lat2,lon2) × road_factor
    Trips = ceil(quantity / vehicle_capacity)
    TransportCost = Distance × cost_per_km × trips
    HandlingCost = handling_per_point × 2 × trips
    TotalLogistics = TransportCost + HandlingCost + SpoilageBuffer
    CostPerKg = TotalLogistics / quantity
    BuyerPrice = FarmerPayout + CostPerKg + PlatformFee

All costs in ₹, distance in km, quantity in kg.
"""
from app.logistics.distance import calculate_distance_km, calculate_distance_with_road_factor
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
)

__all__ = [
    "calculate_distance_km",
    "calculate_distance_with_road_factor",
    "calculate_logistics_cost",
    "calculate_buyer_price",
    "calculate_required_trips",
    "validate_logistics_inputs",
    "validate_coordinates",
    "LogisticsValidationError",
    "estimate_logistics",
    "estimate_logistics_with_pricing",
    "select_vehicle_class",
]
