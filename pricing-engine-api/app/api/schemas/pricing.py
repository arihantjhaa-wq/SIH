"""Pricing API schemas — Request and Response models for Stage 9 API.

These schemas define the HTTP contract for the pricing engine API.
They wrap the existing Stage 6-8 pricing pipeline without duplicating business logic.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class Coordinate(BaseModel):
    """Geographic coordinate."""
    lat: float = Field(..., description="Latitude (-90 to 90)", ge=-90, le=90)
    lon: float = Field(..., description="Longitude (-180 to 180)", ge=-180, le=180)

    @field_validator("lat", "lon")
    @classmethod
    def validate_finite(cls, v: float) -> float:
        import math
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Coordinate must be finite")
        return v


class PricingRequest(BaseModel):
    """Request model for pricing estimate endpoint."""
    commodity: str = Field(
        ...,
        description="Commodity name (e.g., 'Tomato', 'Onion')",
        min_length=1,
        examples=["Tomato"],
    )
    quantity_kg: float = Field(
        ...,
        description="Quantity in kg (must be > 0)",
        gt=0,
        examples=[500.0],
    )
    farmer_location: Coordinate = Field(
        ...,
        description="Farmer's location coordinates",
    )
    buyer_location: Coordinate = Field(
        ...,
        description="Buyer's location coordinates",
    )
    farmer_declared_minimum: Optional[float] = Field(
        None,
        description="Optional minimum price per kg the farmer will accept",
        ge=0,
    )
    platform_fee_pct: Optional[float] = Field(
        None,
        description="Platform fee as fraction of farmer payout (default 0.05 = 5%)",
        ge=0,
        le=1,
    )

    @field_validator("quantity_kg")
    @classmethod
    def validate_quantity_finite(cls, v: float) -> float:
        import math
        if math.isnan(v) or math.isinf(v):
            raise ValueError("quantity_kg must be finite")
        return v


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class PriceRange(BaseModel):
    """Price range information."""
    low: Optional[float] = None
    high: Optional[float] = None
    spread: Optional[float] = None


class FarmerProtection(BaseModel):
    """Farmer protection floor information."""
    floor_per_kg: Optional[float] = None
    blocked: bool = False
    status: str = "OK"


class PricingExplanation(BaseModel):
    """Pricing-side explanation."""
    baseline_price_per_kg: Optional[float] = None
    forecast_price_per_kg: Optional[float] = None
    ml_available: bool = False
    fair_price_per_kg: Optional[float] = None
    price_range: Optional[PriceRange] = None
    reliability_score: Optional[int] = None
    volatility_30d: Optional[float] = None
    demand_index: Optional[float] = None
    farmer_protection: Optional[FarmerProtection] = None
    forecast_drivers: List[Dict[str, Any]] = []
    pricing_constraints: List[Dict[str, Any]] = []
    fallbacks_used: List[str] = []
    model_version: Optional[str] = None

    model_config = {"protected_namespaces": ()}


class LogisticsBreakdown(BaseModel):
    """Logistics cost breakdown."""
    transport: float = 0.0
    handling: float = 0.0
    spoilage_buffer: float = 0.0


class LogisticsExplanation(BaseModel):
    """Logistics-side explanation."""
    distance_km: float = 0.0
    is_estimated: bool = False
    fallback_reason: Optional[str] = None
    vehicle_capacity_kg: Optional[float] = None
    required_trips: Optional[int] = None
    breakdown: LogisticsBreakdown = LogisticsBreakdown()
    total_logistics_cost: float = 0.0
    cost_per_kg: float = 0.0


class PriceBreakdown(BaseModel):
    """Per-kg price breakdown."""
    farmer_payout_per_kg: float = 0.0
    logistics_cost_per_kg: float = 0.0
    platform_fee_pct: float = 0.05
    platform_fee_per_kg: float = 0.0
    buyer_price_per_kg: float = 0.0


class Totals(BaseModel):
    """Total costs for the quantity."""
    farmer_total: float = 0.0
    logistics_total: float = 0.0
    platform_total: float = 0.0
    buyer_total: float = 0.0


class FinalExplanation(BaseModel):
    """Combined explanation payload."""
    pricing: Optional[PricingExplanation] = None
    logistics: Optional[LogisticsExplanation] = None
    price_breakdown: Optional[PriceBreakdown] = None
    totals: Optional[Totals] = None


class PricingResponse(BaseModel):
    """Response model for pricing estimate endpoint."""
    # Identifiers
    commodity_id: Optional[str] = None
    mandi_id: Optional[str] = None
    as_of_date: Optional[str] = None

    # Pricing
    baseline_price_per_kg: Optional[float] = None
    forecast_price_per_kg: Optional[float] = None
    fair_price_per_kg: Optional[float] = None
    farmer_payout_per_kg: Optional[float] = None

    # Price range
    price_range_low: Optional[float] = None
    price_range_high: Optional[float] = None
    price_range_spread: Optional[float] = None

    # Reliability
    reliability_score: Optional[int] = None

    # Farmer protection
    protected_floor: Optional[float] = None
    floor_blocked: bool = False
    floor_status: str = "OK"
    floor_margin: Optional[float] = None

    # Logistics
    distance_km: Optional[float] = None
    vehicle_class: Optional[str] = None
    vehicle_capacity_kg: Optional[float] = None
    required_trips: Optional[int] = None
    transport_cost: Optional[float] = None
    handling_cost: Optional[float] = None
    spoilage_buffer: Optional[float] = None
    total_logistics_cost: Optional[float] = None
    logistics_cost_per_kg: Optional[float] = None

    # Platform
    platform_fee_pct: float = 0.05
    platform_fee_per_kg: Optional[float] = None

    # Final buyer price
    buyer_price_per_kg: Optional[float] = None
    buyer_total: Optional[float] = None

    # Quantity
    quantity_kg: Optional[float] = None

    # Totals
    farmer_total: Optional[float] = None
    logistics_total: Optional[float] = None
    platform_total: Optional[float] = None

    # Fallback
    is_fallback: bool = False
    fallback_reason: Optional[str] = None

    # Explanation
    pricing_explanation: Optional[PricingExplanation] = None
    logistics_explanation: Optional[LogisticsExplanation] = None
    explanation: Optional[FinalExplanation] = None


# ---------------------------------------------------------------------------
# Error Response
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail
