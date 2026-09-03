"""
Prediction Reliability Score — Section 22 (corrected, F5/F6).

Hand-tuned weighted sum of 7 sub-scores (0-100), NOT a calibrated probability.
Sub-components normalized 0-1, then weighted and scaled to 0-100.

Weights:
    DataFreshness:       0.25  (clamp(1 - age_days/7, 0, 1))
    HistoricalVolume:    0.20
    ValidationQuality:   0.20
    MandiAvailability:   0.10
    WeatherAvailability: 0.10
    ModelAgreement:      0.10
    MarketVolatility:    0.05  (1 - volatility_30d, clamped to [0,1])

Volatility cap (F6): when STRESSED (volatility_30d > 30%),
    PredictionReliability = min(computed_reliability, 79)

ModelAgreement default (F5): 0.5 (neutral) when baseline-only mode,
    with "modelAgreementDefault": true disclosed in fallbacksUsed.
"""
from __future__ import annotations

from typing import Optional


# Weights from Section 22
WEIGHTS = {
    "data_freshness": 0.25,
    "historical_volume": 0.20,
    "validation_quality": 0.20,
    "mandi_availability": 0.10,
    "weather_availability": 0.10,
    "model_agreement": 0.10,
    "market_volatility": 0.05,
}

# Reliability band thresholds (for display)
RELIABILITY_BANDS = {
    "HIGH": (80, 100),
    "MEDIUM": (60, 79),
    "LOW": (40, 59),
    "INSUFFICIENT": (0, 39),
}


def _clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def calculate_data_freshness(age_days: float | None) -> float:
    """DataFreshness = clamp(1 - age_days/7, 0, 1)."""
    if age_days is None:
        return 0.0
    return _clamp(1.0 - float(age_days) / 7.0)


def calculate_historical_volume(
    n_observations: int,
    min_required: int = 90,
) -> float:
    """HistoricalVolume: fraction of minimum required observations."""
    return _clamp(float(n_observations) / float(min_required))


def calculate_validation_quality(
    validation_mae: float | None,
    baseline_mae: float | None,
) -> float:
    """
    ValidationQuality: 1 - (ML MAE / Baseline MAE), clamped.
    Higher = better (ML beats baseline).
    """
    if validation_mae is None or baseline_mae is None or baseline_mae < 0.01:
        return 0.5  # neutral default per zero-denominator convention
    ratio = float(validation_mae) / float(baseline_mae)
    return _clamp(1.0 - ratio)


def calculate_mandi_availability(
    mandi_has_data: bool,
) -> float:
    """MandiAvailability: 1.0 if mandi has fresh data, 0.0 otherwise."""
    return 1.0 if mandi_has_data else 0.0


def calculate_weather_availability(
    weather_has_data: bool,
) -> float:
    """WeatherAvailability: 1.0 if weather data available, 0.0 otherwise."""
    return 1.0 if weather_has_data else 0.0


def calculate_model_agreement(
    prophet_pred: float | None,
    ml_pred: float | None,
    baseline_mode: bool = False,
) -> float:
    """
    ModelAgreement per Section 22 (F5).

    - If both Prophet and sklearn active: clamp(1 - |Prophet - ML| / Prophet, 0, 1)
    - If baseline-only (<90 days history): 0.5 (neutral default), with disclosure flag

    Returns:
        (score, is_default) tuple where is_default=True means 0.5 default was used.
    """
    if baseline_mode or prophet_pred is None or ml_pred is None:
        return 0.5, True

    p = float(prophet_pred)
    m = float(ml_pred)

    # Zero-denominator convention (F10): if ProphetPred < 0.01, return neutral
    if p < 0.01:
        return 0.5, True

    agreement = _clamp(1.0 - abs(p - m) / p)
    return agreement, False


def calculate_market_volatility(
    volatility_30d: float | None,
) -> float:
    """
    MarketVolatility = 1 - volatility_30d, clamped to [0,1].
    Higher = less volatile = better.
    """
    if volatility_30d is None:
        return 1.0  # no volatility data = assume stable
    vol = float(volatility_30d)
    vol = _clamp(vol)  # ensure [0,1]
    return _clamp(1.0 - vol)


def calculate_reliability_score(
    *,
    data_freshness: float,
    historical_volume: float,
    validation_quality: float,
    mandi_availability: float,
    weather_availability: float,
    model_agreement: float,
    market_volatility: float,
    volatility_30d: float | None = None,
    model_agreement_default: bool = False,
) -> dict:
    """
    Compute full Prediction Reliability Score (0-100).

    Args:
        All 7 sub-scores in 0-1 range.
        volatility_30d: Optional raw volatility for STRESSED cap check.
        model_agreement_default: Whether model_agreement used neutral default.

    Returns:
        {
            "reliability": int (0-100),
            "band": "HIGH"|"MEDIUM"|"LOW"|"INSUFFICIENT",
            "subscores": { ... },
            "weights": { ... },
            "volatility_capped": bool,
            "model_agreement_default": bool,
        }
    """
    # Weighted sum
    weighted = (
        WEIGHTS["data_freshness"] * data_freshness
        + WEIGHTS["historical_volume"] * historical_volume
        + WEIGHTS["validation_quality"] * validation_quality
        + WEIGHTS["mandi_availability"] * mandi_availability
        + WEIGHTS["weather_availability"] * weather_availability
        + WEIGHTS["model_agreement"] * model_agreement
        + WEIGHTS["market_volatility"] * market_volatility
    )

    reliability = round(100.0 * weighted)
    reliability = max(0, min(100, reliability))

    # Volatility cap (F6): STRESSED = volatility_30d > 30%
    volatility_capped = False
    if volatility_30d is not None and float(volatility_30d) > 0.30:
        if reliability > 79:
            reliability = 79
            volatility_capped = True

    # Determine band
    band = "INSUFFICIENT"
    for name, (lo, hi) in RELIABILITY_BANDS.items():
        if lo <= reliability <= hi:
            band = name
            break

    return {
        "reliability": reliability,
        "band": band,
        "subscores": {
            "data_freshness": round(data_freshness, 3),
            "historical_volume": round(historical_volume, 3),
            "validation_quality": round(validation_quality, 3),
            "mandi_availability": round(mandi_availability, 3),
            "weather_availability": round(weather_availability, 3),
            "model_agreement": round(model_agreement, 3),
            "market_volatility": round(market_volatility, 3),
        },
        "weights": WEIGHTS,
        "volatility_capped": volatility_capped,
        "model_agreement_default": model_agreement_default,
    }


def get_reliability_band_label(reliability: int) -> str:
    """Get human-readable band label from reliability score."""
    for name, (lo, hi) in RELIABILITY_BANDS.items():
        if lo <= reliability <= hi:
            return name
    return "INSUFFICIENT"