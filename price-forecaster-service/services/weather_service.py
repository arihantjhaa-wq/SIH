"""
Weather service — fetch historical and forecast weather data from Open-Meteo.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple
from config import settings


class WeatherError(Exception):
    """Weather data fetch failed."""
    pass


class WeatherService:
    """Fetch weather data from Open-Meteo API."""

    @staticmethod
    def fetch_weather(
        latitude: float,
        longitude: float,
        days_historical: int = 30
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch historical and 7-day forecast weather.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            days_historical: Number of historical days to fetch

        Returns:
            (historical_df, forecast_df)
            Each with columns: date, max_temp, rainfall_mm
        """
        try:
            hist_df = WeatherService._fetch_historical(
                latitude,
                longitude,
                days_historical
            )
            forecast_df = WeatherService._fetch_forecast(latitude, longitude)

            print(
                f"[Weather] Fetched {len(hist_df)} historical, "
                f"{len(forecast_df)} forecast days"
            )
            return hist_df, forecast_df

        except Exception as e:
            raise WeatherError(f"Weather fetch failed: {e}")

    @staticmethod
    def _fetch_historical(
        latitude: float,
        longitude: float,
        days: int
    ) -> pd.DataFrame:
        """Fetch historical weather from Open-Meteo Archive API."""
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "daily": ["temperature_2m_max", "rain_sum"],
            "timezone": settings.TIMEZONE
        }

        try:
            response = requests.get(
                settings.OPEN_METEO_ARCHIVE_URL,
                params=params,
                timeout=settings.OPEN_METEO_TIMEOUT
            )
            data = response.json()

            df = pd.DataFrame({
                "date": pd.to_datetime(data["daily"]["time"]),
                "max_temp": data["daily"]["temperature_2m_max"],
                "rainfall_mm": data["daily"]["rain_sum"]
            })

            # Forward fill then backward fill missing values
            df = df.bfill().ffill()

            return df

        except Exception as e:
            raise WeatherError(f"Historical fetch failed: {e}")

    @staticmethod
    def _fetch_forecast(latitude: float, longitude: float) -> pd.DataFrame:
        """Fetch 7-day forecast from Open-Meteo Forecast API."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ["temperature_2m_max", "rain_sum"],
            "timezone": settings.TIMEZONE,
            "forecast_days": settings.FORECAST_DAYS
        }

        try:
            response = requests.get(
                settings.OPEN_METEO_FORECAST_URL,
                params=params,
                timeout=settings.OPEN_METEO_TIMEOUT
            )
            data = response.json()

            df = pd.DataFrame({
                "date": pd.to_datetime(data["daily"]["time"]),
                "max_temp": data["daily"]["temperature_2m_max"],
                "rainfall_mm": data["daily"]["rain_sum"]
            })

            # Forward fill then backward fill missing values
            df = df.bfill().ffill()

            return df

        except Exception as e:
            raise WeatherError(f"Forecast fetch failed: {e}")
