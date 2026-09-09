"""
Pydantic models for request/response validation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ForecastRequest(BaseModel):
    """Request to predict 7-day price forecast."""

    state: str = Field(..., description="State name (e.g., West Bengal)")
    commodity: str = Field(..., description="Commodity/crop name (e.g., Tomato)")

    @field_validator("state", "commodity")
    @classmethod
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        if len(v.strip()) > 100:
            raise ValueError("Field too long (max 100 characters)")
        return v.strip()


class ResolvedLocation(BaseModel):
    """Geocoded location details."""

    address: str = Field(..., description="Full resolved address")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    source: Optional[str] = Field(
        None,
        description="Geocoding source (google_maps, nominatim)"
    )


class DailyForecast(BaseModel):
    """One day's forecast."""

    date: str = Field(..., description="ISO 8601 date (YYYY-MM-DD)")
    predicted_price_inr_per_kg: float = Field(
        ...,
        description="Predicted price in ₹/kg"
    )
    rainfall_mm: float = Field(..., description="Expected rainfall in mm")
    temperature_c: float = Field(..., description="Maximum temperature in °C")


class Trend(BaseModel):
    """Market trend analysis."""

    direction: str = Field(
        ...,
        description="rising, falling, or stable"
    )
    change_percent: float = Field(
        ...,
        description="Percentage change from first to last day"
    )
    first_price_inr: float = Field(..., description="Price on first day")
    last_price_inr: float = Field(..., description="Price on last day")


class ForecastResponse(BaseModel):
    """Complete 7-day forecast response."""

    commodity: str = Field(..., description="Requested commodity")
    state: str = Field(..., description="Requested state")
    forecast: List[DailyForecast] = Field(
        ...,
        description="7-day forecast array"
    )
    trend: Trend = Field(..., description="Market trend analysis")
    data_source: str = Field(
        default="model",
        description="Source of forecast: model, fallback"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp when forecast was generated"
    )
