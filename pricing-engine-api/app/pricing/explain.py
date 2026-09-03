"""
Explanation Output — Section 23 (corrected, F1.3).

Distinguishes:
  (a) model inputs/signals that shaped the Forecast (forecastDrivers)
  (b) downstream pricing constraints (pricingConstraints)

forecastDrivers entries are model-attributed, NOT independent formula terms.
pricingConstraints lists hard constraints applied after Section 15.
"""
from __future__ import annotations

from typing import Any, Optional


def build_forecast_drivers(
    features: dict | None = None,
    market_features: dict | None = None,
    demand_index: float | None = None,
    weather_features: dict | None = None,
    ml_available: bool = False,
) -> list:
    """
    Build forecastDrivers array — Section 23.
    All entries have role: "model_input".
    """
    drivers = []

    # Primary driver: recent mandi price trends
    drivers.append({
        "factor": "Recent mandi price trend (lags/rolling stats)",
        "role": "model_input",
        "attribution": "primary",
    })

    # Demand signal (if available)
    if demand_index is not None and demand_index > 0:
        drivers.append({
            "factor": f"Demand signal (order activity, {int(demand_index)}/100)",
            "role": "model_input",
            "attribution": "moderate",
        })

    # Weather signal (if available)
    if weather_features is not None:
        rainfall = weather_features.get("rainfall_mm")
        if rainfall is not None and rainfall > 0:
            drivers.append({
                "factor": f"Weather: rainfall {rainfall:.1f}mm",
                "role": "model_input",
                "attribution": "minor",
            })

    # Regional differential (if available from market features)
    if market_features is not None:
        regional_median = market_features.get("regional_median")
        lag_1 = market_features.get("lag_1")
        if regional_median is not None and lag_1 is not None:
            diff = round(float(lag_1) - float(regional_median), 2)
            if abs(diff) > 0:
                direction = "above" if diff > 0 else "below"
                drivers.append({
                    "factor": f"Regional price differential vs. state median ({abs(diff)} ₹/kg {direction})",
                    "role": "model_input",
                    "attribution": "minor",
                })

    return drivers


def build_pricing_constraints(
    floor_blocked: bool = False,
    floor_margin: float | None = None,
    floor_reason: str | None = None,
    volatility_capped: bool = False,
    volatility_30d: float | None = None,
) -> list:
    """
    Build pricingConstraints array — Section 23.
    All entries have role: "constraint" with triggered boolean.
    """
    constraints = []

    # Farmer protection floor
    constraints.append({
        "factor": "Farmer protection floor (85% of baseline)",
        "role": "constraint",
        "triggered": floor_blocked,
        **({"reason": floor_reason} if floor_reason else {}),
    })

    # Volatility-based range widening
    vol_stressed = volatility_30d is not None and float(volatility_30d) > 0.30
    constraints.append({
        "factor": "Volatility-based range widening",
        "role": "constraint",
        "triggered": vol_stressed,
        **({"volatility_30d": float(volatility_30d)} if volatility_30d else {}),
    })

    return constraints


def get_market_condition(
    demand_index: float | None = None,
    volatility_30d: float | None = None,
) -> str:
    """
    Derive market condition label for display.
    Based on demand index and volatility levels.
    """
    vol = float(volatility_30d) if volatility_30d is not None else 0.0
    demand = float(demand_index) if demand_index is not None else 50.0

    if vol > 0.30:
        return "VOLATILE"
    if demand >= 80:
        return "EXTREME_DEMAND"
    if demand >= 60:
        return "MODERATE_DEMAND"
    if demand >= 30:
        return "NORMAL"
    return "LOW_DEMAND"


def get_volatility_label(volatility_30d: float | None) -> str:
    """Market volatility label: NORMAL (<15%), ELEVATED (15-30%), STRESSED (>30%)."""
    vol = float(volatility_30d) if volatility_30d is not None else 0.0
    if vol > 0.30:
        return "STRESSED"
    if vol >= 0.15:
        return "ELEVATED"
    return "NORMAL"


def build_explanation(
    *,
    fair_price: float,
    fair_price_range: dict,
    reliability_result: dict,
    baseline: float,
    forecast: float | None = None,
    ml_available: bool = False,
    baseline_only: bool = False,
    features: dict | None = None,
    demand_index: float | None = None,
    weather_features: dict | None = None,
    floor_blocked: bool = False,
    floor_margin: float | None = None,
    floor_reason: str | None = None,
    volatility_30d: float | None = None,
    volatility_capped: bool = False,
    model_version: str | None = None,
    fallbacks_used: list | None = None,
    data_source: str | None = None,
) -> dict:
    """
    Build the complete explanation payload — Section 23 format.

    Returns the full explanation dict matching the spec's JSON structure.
    """
    # Build forecastDrivers
    forecast_drivers = build_forecast_drivers(
        features=features,
        market_features=features,
        demand_index=demand_index,
        weather_features=weather_features,
        ml_available=ml_available,
    )

    # Build pricingConstraints
    pricing_constraints = build_pricing_constraints(
        floor_blocked=floor_blocked,
        floor_margin=floor_margin,
        floor_reason=floor_reason,
        volatility_capped=volatility_capped,
        volatility_30d=volatility_30d,
    )

    # Determine market condition
    market_condition = get_market_condition(
        demand_index=demand_index,
        volatility_30d=volatility_30d,
    )

    # Volatility label
    volatility_label = get_volatility_label(volatility_30d)

    # Fallbacks used
    fallbacks = list(fallbacks_used) if fallbacks_used else []

    # Add model agreement default if applicable
    if baseline_only:
        fallbacks.append("modelAgreementDefault")

    # Build final explanation payload
    explanation = {
        "recommendedPrice": fair_price,
        "range": {
            "min": fair_price_range["lower"],
            "max": fair_price_range["upper"],
        },
        "reliability": reliability_result["reliability"],
        "reliabilityBreakdown": {
            "dataFreshness": reliability_result["subscores"]["data_freshness"],
            "historicalVolume": reliability_result["subscores"]["historical_volume"],
            "validationQuality": reliability_result["subscores"]["validation_quality"],
            "mandiAvailability": reliability_result["subscores"]["mandi_availability"],
            "weatherAvailability": reliability_result["subscores"]["weather_availability"],
            "modelAgreement": reliability_result["subscores"]["model_agreement"],
            "marketVolatility": reliability_result["subscores"]["market_volatility"],
        },
        "modelAgreementDefault": baseline_only,
        "marketCondition": market_condition,
        "priceVolatility": volatility_label,
        "forecastDrivers": forecast_drivers,
        "pricingConstraints": pricing_constraints,
        "fallbacksUsed": fallbacks,
        "modelVersion": model_version,
    }

    # Optional: add data source if provided
    if data_source:
        explanation["dataSource"] = data_source

    return explanation
