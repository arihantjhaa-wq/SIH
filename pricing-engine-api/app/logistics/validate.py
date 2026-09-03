"""
Input validation for logistics calculations.

Returns structured errors consistent with FastAPI conventions.
"""
import math
from typing import Dict, Any, Optional, List


class LogisticsValidationError(Exception):
    """Structured validation error for logistics inputs."""

    def __init__(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "field": self.field,
            "message": self.message,
        }


def validate_coordinates(
    lat: Optional[float],
    lon: Optional[float],
    field_prefix: str = "location",
) -> List[LogisticsValidationError]:
    """
    Validate latitude/longitude pair.

    Args:
        lat: Latitude value
        lon: Longitude value
        field_prefix: Prefix for error field names

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if lat is None or lon is None:
        errors.append(LogisticsValidationError(
            field=f"{field_prefix}",
            message=f"{field_prefix} requires both latitude and longitude",
        ))
        return errors

    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        errors.append(LogisticsValidationError(
            field=f"{field_prefix}",
            message=f"{field_prefix} coordinates must be numeric",
        ))
        return errors

    if math.isnan(lat) or math.isinf(lat) or math.isnan(lon) or math.isinf(lon):
        errors.append(LogisticsValidationError(
            field=f"{field_prefix}",
            message=f"{field_prefix} coordinates must be finite",
        ))
        return errors

    if not (-90 <= lat <= 90):
        errors.append(LogisticsValidationError(
            field=f"{field_prefix}.lat",
            message=f"Latitude must be between -90 and 90, got {lat}",
        ))

    if not (-180 <= lon <= 180):
        errors.append(LogisticsValidationError(
            field=f"{field_prefix}.lon",
            message=f"Longitude must be between -180 and 180, got {lon}",
        ))

    return errors


def validate_logistics_inputs(
    farmer_lat: Optional[float],
    farmer_lon: Optional[float],
    buyer_lat: Optional[float],
    buyer_lon: Optional[float],
    quantity_kg: Optional[float],
    vehicle_capacity_kg: Optional[float],
    cost_per_km: Optional[float],
) -> List[LogisticsValidationError]:
    """
    Validate all logistics inputs together.

    Args:
        farmer_lat, farmer_lon: Farmer location
        buyer_lat, buyer_lon: Buyer location
        quantity_kg: Shipment quantity
        vehicle_capacity_kg: Vehicle capacity
        cost_per_km: Cost per kilometer

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate coordinates
    errors.extend(validate_coordinates(farmer_lat, farmer_lon, "farmer_location"))
    errors.extend(validate_coordinates(buyer_lat, buyer_lon, "buyer_location"))

    # Validate quantity
    if quantity_kg is None:
        errors.append(LogisticsValidationError(
            field="quantity_kg",
            message="quantity_kg is required",
        ))
    elif not isinstance(quantity_kg, (int, float)):
        errors.append(LogisticsValidationError(
            field="quantity_kg",
            message="quantity_kg must be numeric",
        ))
    elif math.isnan(quantity_kg) or math.isinf(quantity_kg):
        errors.append(LogisticsValidationError(
            field="quantity_kg",
            message="quantity_kg must be finite",
        ))
    elif quantity_kg <= 0:
        errors.append(LogisticsValidationError(
            field="quantity_kg",
            message=f"quantity_kg must be > 0, got {quantity_kg}",
        ))

    # Validate vehicle capacity
    if vehicle_capacity_kg is None:
        errors.append(LogisticsValidationError(
            field="vehicle_capacity_kg",
            message="vehicle_capacity_kg is required",
        ))
    elif not isinstance(vehicle_capacity_kg, (int, float)):
        errors.append(LogisticsValidationError(
            field="vehicle_capacity_kg",
            message="vehicle_capacity_kg must be numeric",
        ))
    elif math.isnan(vehicle_capacity_kg) or math.isinf(vehicle_capacity_kg):
        errors.append(LogisticsValidationError(
            field="vehicle_capacity_kg",
            message="vehicle_capacity_kg must be finite",
        ))
    elif vehicle_capacity_kg <= 0:
        errors.append(LogisticsValidationError(
            field="vehicle_capacity_kg",
            message=f"vehicle_capacity_kg must be > 0, got {vehicle_capacity_kg}",
        ))

    # Validate cost per km
    if cost_per_km is None:
        errors.append(LogisticsValidationError(
            field="cost_per_km",
            message="cost_per_km is required",
        ))
    elif not isinstance(cost_per_km, (int, float)):
        errors.append(LogisticsValidationError(
            field="cost_per_km",
            message="cost_per_km must be numeric",
        ))
    elif math.isnan(cost_per_km) or math.isinf(cost_per_km):
        errors.append(LogisticsValidationError(
            field="cost_per_km",
            message="cost_per_km must be finite",
        ))
    elif cost_per_km < 0:
        errors.append(LogisticsValidationError(
            field="cost_per_km",
            message=f"cost_per_km must be >= 0, got {cost_per_km}",
        ))

    return errors