"""
Distance calculation module - MVP Haversine formula.

Uses straight-line distance with road-distance multiplier for MVP.
Straight-line × 1.3 is an acceptable approximation for V0.1 (Section 19).
"""
import math
from typing import Optional


# Earth's radius in kilometers
EARTH_RADIUS_KM = 6371.0


def calculate_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate straight-line distance using Haversine formula.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (degrees)
        lat2, lon2: Latitude and longitude of point 2 (degrees)

    Returns:
        Distance in kilometers

    Raises:
        ValueError: If coordinates are invalid
    """
    # Validate coordinates
    if not all(isinstance(coord, (int, float)) for coord in [lat1, lon1, lat2, lon2]):
        raise ValueError("Coordinates must be numeric")

    if not all([-90 <= coord <= 90 for coord in [lat1, lat2]]):
        raise ValueError("Latitude must be between -90 and 90")

    if not all([-180 <= coord <= 180 for coord in [lon1, lon2]]):
        raise ValueError("Longitude must be between -180 and 180")

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


def calculate_distance_with_road_factor(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    road_factor: float = 1.3,
) -> float:
    """
    Calculate road distance using Haversine × road factor.

    Args:
        lat1, lon1: Origin coordinates
        lat2, lon2: Destination coordinates
        road_factor: Multiplier for straight-line to road distance (default 1.3)

    Returns:
        Estimated road distance in kilometers
    """
    straight_line = calculate_distance_km(lat1, lon1, lat2, lon2)
    return straight_line * road_factor