"""
Configuration for AgriDirect Price Forecaster Service.
Loads environment variables and provides centralized settings.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """FastAPI settings from environment variables."""

    # API Configuration
    PORT: int = int(os.getenv("PORT", "8002"))
    HOST: str = "0.0.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # External APIs
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    OPEN_METEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    OPEN_METEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/search"

    # Dataset
    DATASET_FILE: str = os.getenv(
        "DATASET_FILE",
        "india_agricultural_prices_last_5_days_june_september_2026.json"
    )

    # API Timeouts (seconds)
    GOOGLE_MAPS_TIMEOUT: int = 10
    OPEN_METEO_TIMEOUT: int = 15
    NOMINATIM_TIMEOUT: int = 10

    # Forecast Configuration
    FORECAST_DAYS: int = 7
    HISTORICAL_DAYS: int = 30
    TIMEZONE: str = "Asia/Kolkata"

    # Model Configuration
    RF_N_ESTIMATORS: int = 100
    RF_RANDOM_STATE: int = 42

    # Fallback Pricing
    BASE_PRICE_INR: float = 120.0
    RAINFALL_COEFFICIENT: float = 1.2

    # Trend Thresholds
    STABLE_THRESHOLD: float = 1.0  # percentage

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
