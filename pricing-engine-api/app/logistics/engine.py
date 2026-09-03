"""
Logistics Engine - MVP Logistics Calculation Layer (Stage 7).

Transforms:
    Farmer Location + Buyer Location + Quantity + Vehicle Config
                    ↓
              Distance (km)
                    ↓
       Logistics Cost (₹ per shipment)
                    ↓
       Logistics Cost per kg (₹/kg)

Integrates with pricing:
    Farmer Fair Price + Logistics Cost/kg + Platform Fee → Buyer Price

All calculations are deterministic and explainable.
"""
from typing import Dict, Any, Optional
import yaml
from pathlib import Path
import math

from app.logistics.distance import calculate_distance_km, calculate_distance_with_road_factor
from app.logistics.cost import calculate_logistics_cost, calculate_buyer_price, calculate_required_trips
from app.logistics.validate import validate_logistics_inputs, LogisticsValidationError


# Default logistics config path
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / "logistics.yaml"

# MVP fallback distance (Section 18)
FALLBACK_DISTANCE_KM = 50.0


def _load_logistics_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load logistics configuration from YAML."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        # Fallback defaults if config file missing
        return {
            "vehicle_classes": [
                {"name": "mini_truck", "capacity_kg": 1000, "per_km_rate": 12.0},
            ],
            "handling": {"loading_cost_per_point": 30.0, "unloading_cost_per_point": 30.0},
            "spoilage": {"buffer_cost_per_kg": 0.0},
            "road_distance_multiplier": 1.3,
        }

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def select_vehicle_class(
    quantity_kg: float,
    vehicle_classes: Optional[list] = None,
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Select appropriate vehicle class for quantity.

    Args:
        quantity_kg: Shipment quantity
        vehicle_classes: List of vehicle configs (or None to load from config)
        config_path: Path to logistics config

    Returns:
        Selected vehicle class dict
    """
    if vehicle_classes is None:
        config = _load_logistics_config(config_path)
        vehicle_classes = config.get("vehicle_classes", [])

    if not vehicle_classes:
        raise ValueError("No vehicle classes configured")

    # Sort by capacity (ascending) and find smallest that fits
    sorted_classes = sorted(vehicle_classes, key=lambda v: v["capacity_kg"])
    for vehicle in sorted_classes:
        if quantity_kg <= vehicle["capacity_kg"]:
            return vehicle

    # If quantity exceeds all vehicles, use largest and require multiple trips
    return sorted_classes[-1]


def estimate_logistics(
    farmer_lat: Optional[float],
    farmer_lon: Optional[float],
    buyer_lat: Optional[float],
    buyer_lon: Optional[float],
    quantity_kg: float,
    vehicle_capacity_kg: Optional[float] = None,
    cost_per_km: Optional[float] = None,
    handling_cost_per_point: float = 30.0,
    spoilage_buffer_per_kg: float = 0.0,
    use_road_factor: bool = True,
    road_factor: float = 1.3,
    fallback_distance_km: Optional[float] = None,
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Estimate logistics cost for a shipment.

    Args:
        farmer_lat, farmer_lon: Farmer location coordinates
        buyer_lat, buyer_lon: Buyer location coordinates
        quantity_kg: Shipment quantity in kg
        vehicle_capacity_kg: Vehicle capacity (or auto-select if None)
        cost_per_km: Cost per km (or auto-select if None)
        handling_cost_per_point: Handling cost per point
        spoilage_buffer_per_kg: Spoilage buffer per kg
        use_road_factor: Whether to apply road distance multiplier
        road_factor: Road distance multiplier
        fallback_distance_km: Fallback distance if coords missing (or None)
        config_path: Path to logistics config file

    Returns:
        Dictionary with logistics estimate, including:
        - distance_km: Calculated distance
        - cost breakdown (transport, handling, spoilage)
        - cost_per_kg: Logistics cost per kg
        - is_fallback: Whether fallback distance was used
        - fallback_reason: Reason if fallback used

    Raises:
        LogisticsValidationError: If inputs are invalid (and no fallback allowed)
    """
    # Try to handle missing coordinates with fallback if configured
    has_farmer_coords = farmer_lat is not None and farmer_lon is not None
    has_buyer_coords = buyer_lat is not None and buyer_lon is not None
    is_fallback = False
    fallback_reason = None
    distance_km = None

    if has_farmer_coords and has_buyer_coords:
        # Calculate distance from coordinates
        validate_result = validate_logistics_inputs(
            farmer_lat, farmer_lon, buyer_lat, buyer_lon,
            quantity_kg, vehicle_capacity_kg or 1000, cost_per_km or 12.0
        )
        # Check for coordinate-specific errors
        coord_errors = [e for e in validate_result if "location" in e.field]
        if coord_errors:
            raise coord_errors[0]

        if use_road_factor:
            distance_km = calculate_distance_with_road_factor(
                farmer_lat, farmer_lon, buyer_lat, buyer_lon, road_factor
            )
        else:
            distance_km = calculate_distance_km(farmer_lat, farmer_lon, buyer_lat, buyer_lon)
    else:
        # Missing coordinates - use fallback if provided
        if fallback_distance_km is not None:
            distance_km = fallback_distance_km
            is_fallback = True
            fallback_reason = "farmer or buyer location missing, using fallback distance"
        else:
            raise LogisticsValidationError(
                field="farmer_location" if not has_farmer_coords else "buyer_location",
                message=f"{'farmer' if not has_farmer_coords else 'buyer'} location is required",
            )

    # Auto-select vehicle if not provided
    if vehicle_capacity_kg is None or cost_per_km is None:
        vehicle = select_vehicle_class(quantity_kg, config_path=config_path)
        vehicle_capacity_kg = vehicle_capacity_kg or vehicle["capacity_kg"]
        cost_per_km = cost_per_km or vehicle["per_km_rate"]

    # Validate quantity and vehicle inputs
    other_errors = validate_logistics_inputs(
        farmer_lat or 0, farmer_lon or 0, buyer_lat or 0, buyer_lon or 0,
        quantity_kg, vehicle_capacity_kg, cost_per_km
    )
    quantity_errors = [e for e in other_errors if e.field in ["quantity_kg", "vehicle_capacity_kg", "cost_per_km"]]
    if quantity_errors:
        raise quantity_errors[0]

    # Calculate logistics cost
    cost_result = calculate_logistics_cost(
        distance_km=distance_km,
        quantity_kg=quantity_kg,
        vehicle_capacity_kg=vehicle_capacity_kg,
        cost_per_km=cost_per_km,
        handling_cost_per_point=handling_cost_per_point,
        spoilage_buffer_per_kg=spoilage_buffer_per_kg,
    )

    # Build explainable result
    result = {
        "distance_km": cost_result["distance_km"],
        "quantity_kg": cost_result["quantity_kg"],
        "vehicle_capacity_kg": cost_result["vehicle_capacity_kg"],
        "trips": cost_result["trips"],
        "cost_per_kg": cost_result["cost_per_kg"],
        "total_logistics_cost": cost_result["total_logistics_cost"],
        "transport_cost": cost_result["transport_cost"],
        "handling_cost": cost_result["handling_cost"],
        "spoilage_buffer": cost_result["spoilage_buffer"],
        "breakdown": {
            "transport": cost_result["transport_cost"],
            "handling": cost_result["handling_cost"],
            "spoilageBuffer": cost_result["spoilage_buffer"],
        },
        "is_fallback": is_fallback,
        "fallback_reason": fallback_reason,
        "is_estimated": is_fallback,
    }

    return result


def estimate_logistics_with_pricing(
    pricing_result: Dict[str, Any],
    logistics_result: Dict[str, Any],
    platform_fee_pct: float = 0.05,
) -> Dict[str, Any]:
    """
    Combine pricing result with logistics to produce final buyer price.

    Args:
        pricing_result: Output from predict_price() (contains fair_price, etc.)
        logistics_result: Output from estimate_logistics() (contains cost_per_kg, etc.)
        platform_fee_pct: Platform fee as fraction of farmer payout

    Returns:
        Combined result with buyer price breakdown
    """
    farmer_payout = pricing_result.get("fair_price") or pricing_result.get("baseline", 0)
    logistics_per_kg = logistics_result.get("cost_per_kg", 0)
    quantity = logistics_result.get("quantity_kg", 100)

    # Calculate buyer price
    buyer_price = calculate_buyer_price(
        farmer_payout_per_kg=farmer_payout,
        logistics_cost_per_kg=logistics_per_kg,
        platform_fee_pct=platform_fee_pct,
    )

    # Total costs for quantity
    farmer_total = farmer_payout * quantity
    logistics_total = logistics_per_kg * quantity
    platform_total = buyer_price["platform_fee_per_kg"] * quantity
    buyer_total = buyer_price["buyer_price_per_kg"] * quantity

    return {
        **pricing_result,
        "logistics": logistics_result,
        "logistics_cost_per_kg": logistics_per_kg,
        "platform_fee_per_kg": buyer_price["platform_fee_per_kg"],
        "buyer_price_per_kg": buyer_price["buyer_price_per_kg"],
        "farmer_payout_total": round(farmer_total, 2),
        "logistics_total": round(logistics_total, 2),
        "platform_fee_total": round(platform_total, 2),
        "buyer_price_total": round(buyer_total, 2),
        "breakdown": {
            "farmerPayout": round(farmer_payout, 2),
            "logistics": round(logistics_per_kg, 2),
            "platformFee": round(buyer_price["platform_fee_per_kg"], 2),
            "buyerPrice": round(buyer_price["buyer_price_per_kg"], 2),
        },
    }