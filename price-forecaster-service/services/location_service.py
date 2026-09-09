"""
Location service — geocode addresses using Google Maps and Nominatim.
"""

import requests
from typing import Tuple, Optional
from config import settings


class LocationError(Exception):
    """Location resolution failed."""
    pass


class LocationService:
    """Geocode addresses to coordinates."""

    @staticmethod
    def resolve_address(address: str) -> Tuple[float, float, str]:
        """
        Geocode address to (latitude, longitude, full_address).

        Tries Google Maps first, falls back to Nominatim/OpenStreetMap.

        Args:
            address: Location name or address string

        Returns:
            (lat, lon, formatted_address)

        Raises:
            LocationError: If geocoding fails
        """
        # Try Google Maps first
        if settings.GOOGLE_MAPS_API_KEY:
            try:
                lat, lon, formatted = LocationService._google_maps_geocode(address)
                print(f"[Location] Resolved via Google Maps: {formatted}")
                return lat, lon, formatted
            except Exception as e:
                print(f"[Location] Google Maps failed: {e}")
                # Fall through to Nominatim

        # Fall back to Nominatim (OpenStreetMap)
        try:
            lat, lon, formatted = LocationService._nominatim_geocode(address)
            print(f"[Location] Resolved via Nominatim: {formatted}")
            return lat, lon, formatted
        except Exception as e:
            print(f"[Location] Nominatim failed: {e}")
            raise LocationError(f"Could not locate '{address}'")

    @staticmethod
    def _google_maps_geocode(address: str) -> Tuple[float, float, str]:
        """Geocode using Google Maps API."""
        if not settings.GOOGLE_MAPS_API_KEY:
            raise LocationError("Google Maps API key not configured")

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "key": settings.GOOGLE_MAPS_API_KEY,
            "region": "in"  # India
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=settings.GOOGLE_MAPS_TIMEOUT
            )
            data = response.json()

            if data.get("status") != "OK":
                raise LocationError(f"Status: {data.get('status')}")

            if not data.get("results"):
                raise LocationError("No results")

            result = data["results"][0]
            location = result["geometry"]["location"]
            formatted = result["formatted_address"]

            return float(location["lat"]), float(location["lng"]), formatted

        except requests.RequestException as e:
            raise LocationError(f"API request failed: {e}")

    @staticmethod
    def _nominatim_geocode(address: str) -> Tuple[float, float, str]:
        """Geocode using Nominatim (OpenStreetMap)."""
        url = settings.NOMINATIM_URL
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": "in"  # Restrict to India
        }
        headers = {
            "User-Agent": "AgriDirect-Forecaster/1.0"
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=settings.NOMINATIM_TIMEOUT
            )
            data = response.json()

            if not data:
                raise LocationError("No results")

            result = data[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            formatted = result.get("display_name", address)

            return lat, lon, formatted

        except (ValueError, KeyError, requests.RequestException) as e:
            raise LocationError(f"Nominatim failed: {e}")
