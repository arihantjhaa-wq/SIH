"""
Pricing Engine — Orchestrator (Sections 15 + 17 + 22 + 23).

Combines:
  - Baseline (Section 8)
  - ML/Baseline forecast (Section 9/12)
  - Price Discovery (Section 15)
  - Farmer Protection Floor (Section 17)
  - Reliability Score (Section 22)
  - Explanation Output (Section 23)

Single entry point: predict_price()
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Optional

# Re-use existing forecasting modules
from app.forecasting.baseline import calculate_baseline
from app.forecasting.sklearn_model import forecast_price
from app.features.engineering import compute_all_features
from app.features.demand import calculate_demand_index
from app.features.weather import get_weather_features
from app.core.db import get_db_session

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
    calculate_validation_quality,
)
from app.pricing.explain import build_explanation


def predict_price(
    commodity_id: str,
    mandi_id: str,
    as_of_date: date,
    w_forecast: float = 0.5,
    farmer_declared_minimum: float | None = None,
    model_path: Optional[Path] = None,
    quantity_kg: float = 100.0,
) -> dict:
    """
    Full pricing pipeline — Sections 15 + 17 + 22 + 23.

    Steps:
      1. Baseline (Section 8)
      2. Forecast (ML or baseline-only) — forecast_price()
      3. Fair Price (Section 15, single blend term)
      4. Spread + Range (Section 15, volatility-aware)
      5. Reliability Score (Section 22, 7 sub-scores)
      6. Farmer Protection Floor (Section 17, hard constraint)
      7. Explanation output (Section 23)

    Args:
        commodity_id: UUID string for the commodity.
        mandi_id: UUID string for the mandi.
        as_of_date: Date for which to predict (point-in-time discipline).
        w_forecast: Weight for forecast vs baseline (default 0.5).
        farmer_declared_minimum: Optional floor override from farmer.
        model_path: Path to trained model pickle (or None for baseline-only).
        quantity_kg: Quantity for buyer price calculation (default 100).

    Returns:
        Comprehensive pricing result dict with all sections.
    """
    # ------------------------------------------------------------------
    # Step 1: Get forecast (includes baseline, market, demand, weather)
    # ------------------------------------------------------------------
    forecast_result = forecast_price(
        commodity_id=commodity_id,
        mandi_id=mandi_id,
        as_of_date=as_of_date,
        model_path=model_path,
    )

    baseline = forecast_result["baseline_forecast"]
    if baseline is None:
        # No baseline available — cannot price
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "No baseline data available for prediction",
            "commodity_id": commodity_id,
            "mandi_id": mandi_id,
            "as_of_date": as_of_date.isoformat(),
        }

    ml_forecast = forecast_result.get("ml_forecast")
    ml_available = forecast_result.get("ml_available", False)
    features = forecast_result.get("features", {})

    # Effective forecast for pricing: prefer ML if available, else baseline
    # Note: In baseline-only mode, FairPrice == Baseline (no blend effect)
    effective_forecast = ml_forecast if ml_forecast is not None else baseline
    baseline_only = not ml_available or ml_forecast is None

    # Extract feature values for reliability/spread
    volatility_30d = features.get("volatility_30d")
    demand_index = features.get("demand_index", 0.0)
    rainfall_mm = features.get("rainfall_mm")
    temp_max_c = features.get("temp_max_c")
    lag_1 = features.get("lag_1")
    rolling_mean_7 = features.get("rolling_mean_7")

    # ------------------------------------------------------------------
    # Step 2: Price Discovery — FairPrice (Section 15)
    # ------------------------------------------------------------------
    fair_price = calculate_fair_price(
        baseline=baseline,
        forecast=effective_forecast,
        w_forecast=w_forecast,
    )

    # ------------------------------------------------------------------
    # Step 3: Reliability Score (Section 22) — must compute before spread
    #         because spread depends on reliability
    # ------------------------------------------------------------------
    # Compute sub-scores
    # Data freshness: derived from how recent lag_1 price is
    # For now, assume fresh (0 days) if we have data, stale otherwise
    data_freshness = 1.0 if lag_1 is not None else 0.0
    historical_volume = 1.0 if not baseline_only else 0.3  # penalize limited history
    validation_quality = 0.5  # neutral if no validation metrics available
    mandi_availability = 1.0 if lag_1 is not None else 0.0
    weather_availability = 1.0 if rainfall_mm is not None else 0.0

    # Model agreement
    if baseline_only:
        model_agreement = 0.5
        model_agreement_default = True
    else:
        # In ML mode, agreement between baseline and ML prediction
        # Use baseline as "prophet" proxy for now (single ML model)
        agreement, is_default = calculate_model_agreement(
            prophet_pred=baseline,
            ml_pred=ml_forecast,
            baseline_mode=False,
        )
        model_agreement = agreement
        model_agreement_default = is_default

    market_vol = calculate_market_volatility(volatility_30d)

    reliability_result = calculate_reliability_score(
        data_freshness=data_freshness,
        historical_volume=historical_volume,
        validation_quality=validation_quality,
        mandi_availability=mandi_availability,
        weather_availability=weather_availability,
        model_agreement=model_agreement,
        market_volatility=market_vol,
        volatility_30d=volatility_30d,
        model_agreement_default=model_agreement_default,
    )

    # ------------------------------------------------------------------
    # Step 4: Spread + Range (Section 15)
    # ------------------------------------------------------------------
    spread = calculate_spread(
        volatility_30d=volatility_30d,
        reliability=reliability_result["reliability"],
    )
    fair_price_range = calculate_fair_price_range(fair_price, spread)

    # ------------------------------------------------------------------
    # Step 5: Farmer Protection Floor (Section 17)
    # ------------------------------------------------------------------
    floor = calculate_farmer_floor(
        baseline=baseline,
        farmer_declared_minimum=farmer_declared_minimum,
    )
    floor_check = check_floor_protection(
        fair_price_lower=fair_price_range["lower"],
        floor=floor,
    )

    # ------------------------------------------------------------------
    # Step 6: Explanation (Section 23)
    # ------------------------------------------------------------------
    weather_features = {
        "rainfall_mm": rainfall_mm,
        "temp_max_c": temp_max_c,
    }
    explanation = build_explanation(
        fair_price=fair_price,
        fair_price_range=fair_price_range,
        reliability_result=reliability_result,
        baseline=baseline,
        forecast=ml_forecast,
        ml_available=ml_available,
        baseline_only=baseline_only,
        features=features,
        demand_index=demand_index,
        weather_features=weather_features,
        floor_blocked=floor_check["blocked"],
        floor_margin=floor_check["margin_above_floor"],
        floor_reason=floor_check["reason"],
        volatility_30d=volatility_30d,
        volatility_capped=reliability_result["volatility_capped"],
        model_version="baseline" if baseline_only else None,
        fallbacks_used=[],
    )

    # ------------------------------------------------------------------
    # Step 7: Final buyer price placeholder (Section 21)
    #         Full logistics integration deferred to Day 10
    # ------------------------------------------------------------------
    platform_fee_per_kg = 0.05 * fair_price  # ASSUMPTION: 5% platform fee
    buyer_price_per_kg = fair_price  # + logistics (Day 10)

    result = {
        "status": "OK",
        "commodity_id": commodity_id,
        "mandi_id": mandi_id,
        "as_of_date": as_of_date.isoformat(),
        "baseline": round(float(baseline), 2),
        "ml_forecast": ml_forecast,
        "ml_available": ml_available,
        "fair_price": fair_price,
        "spread": spread,
        "fair_price_range": fair_price_range,
        "reliability": reliability_result["reliability"],
        "reliability_breakdown": reliability_result["subscores"],
        "reliability_band": reliability_result["band"],
        "floor": floor,
        "floor_blocked": floor_check["blocked"],
        "floor_status": floor_check["status"],
        "floor_margin": floor_check["margin_above_floor"],
        "pricing_constraints": explanation["pricingConstraints"],
        "explanation": explanation,
        "features": features,
        "volatility_30d": volatility_30d,
        "demand_index": demand_index,
    }

    # If floor triggered, override status
    if floor_check["blocked"]:
        result["status"] = "BLOCKED"
        result["floor_reason"] = floor_check["reason"]

    return result
