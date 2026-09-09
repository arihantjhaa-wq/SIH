import requests
from datetime import datetime
from typing import Optional
from config import settings


class GoogleMapsError(Exception):
    """Raised when Google Maps API returns an error."""
    pass


def get_route_from_google_maps(
    origin_address: str,
    destination_address: str,
    departure_dt: datetime
) -> dict:
    """
    Fetch route information from Google Maps Distance Matrix API.

    The Distance Matrix API is the one enabled on this Google Cloud project
    and is the same API the original CLI transportation algorithm used.
    It returns distance and traffic-aware duration which feed the cost and
    transit time calculations.

    NOTE: The Distance Matrix API does not return a route polyline.
    To get a map route, the newer Directions (New) or Routes API would be
    needed — but neither is enabled on this project's billing account.
    If you later enable Routes API, update this function to extract
    overview_polyline from the routes response and return route_points.

    Returns:
        Dictionary with:
        - origin_address: Normalized origin from Google
        - destination_address: Normalized destination from Google
        - distance_km: Distance in kilometers
        - distance_text: Human-readable distance
        - duration_seconds: Duration in seconds (car travel time with traffic)
        - duration_text: Human-readable duration
        - route_polyline: Empty string (not available from Distance Matrix)
        - route_points: Empty list (not available from Distance Matrix)
    """
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        raise GoogleMapsError("Google Maps API key not configured")

    departure_timestamp = int(departure_dt.timestamp())

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin_address,
        "destinations": destination_address,
        "departure_time": departure_timestamp,
        "traffic_model": "best_guess",
        "key": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise GoogleMapsError(f"Failed to connect to Google Maps API: {str(e)}")

    if data.get("status") != "OK":
        error_msg = data.get("error_message", data.get("status"))
        raise GoogleMapsError(f"Google API Error: {error_msg}")

    rows = data.get("rows")
    if not rows or not rows[0].get("elements"):
        raise GoogleMapsError("No route found between the provided addresses")

    element = rows[0]["elements"][0]
    if element.get("status") != "OK":
        raise GoogleMapsError(
            f"Google API could not route between these addresses ({element.get('status')})"
        )

    # Extract distance
    distance_meters = element["distance"]["value"]
    distance_km = distance_meters / 1000.0
    distance_text = element["distance"]["text"]

    # Extract duration with traffic — prefer duration_in_traffic when available
    duration_data = element.get("duration_in_traffic") or element.get("duration")
    if not duration_data:
        raise GoogleMapsError("Google Maps did not return duration data")
    duration_seconds = duration_data["value"]
    duration_text = duration_data["text"]

    # Addresses normalized by Google
    origin_normalized = (
        data.get("origin_addresses", [origin_address])[0] if data.get("origin_addresses") else origin_address
    )
    destination_normalized = (
        data.get("destination_addresses", [destination_address])[0] if data.get("destination_addresses") else destination_address
    )

    # Distance Matrix does not return route polyline — leave empty.
    # To get a polyline, enable Routes API or Directions API in the
    # Google Cloud Console and extend this function.
    return {
        "origin_address": origin_normalized,
        "destination_address": destination_normalized,
        "distance_km": distance_km,
        "distance_text": distance_text,
        "duration_seconds": duration_seconds,
        "duration_text": duration_text,
        "route_polyline": "",
        "route_points": [],
    }