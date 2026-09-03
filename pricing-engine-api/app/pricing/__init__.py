"""Pricing engine module — Stage 6 (Sections 15/17/22/23) + Stage 8 Integration"""

from app.pricing.discovery import (
    calculate_fair_price,
    calculate_spread,
    calculate_fair_price_range,
)
from app.pricing.farmer_floor import (
    calculate_farmer_floor,
    check_floor_protection,
)
from app.pricing.reliability import (
    calculate_reliability_score,
    calculate_model_agreement,
    calculate_market_volatility,
    get_reliability_band_label,
)
from app.pricing.explain import build_explanation, build_forecast_drivers, build_pricing_constraints
from app.pricing.engine import predict_price
from app.pricing.integration import compute_end_to_end_price, PricingIntegrationError

__all__ = [
    "calculate_fair_price",
    "calculate_spread",
    "calculate_fair_price_range",
    "calculate_farmer_floor",
    "check_floor_protection",
    "calculate_reliability_score",
    "calculate_model_agreement",
    "calculate_market_volatility",
    "get_reliability_band_label",
    "build_explanation",
    "build_forecast_drivers",
    "build_pricing_constraints",
    "predict_price",
    "compute_end_to_end_price",
    "PricingIntegrationError",
]