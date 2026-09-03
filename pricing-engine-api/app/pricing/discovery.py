"""
Price Discovery module — Section 15 (corrected, F1).

Single blend term only:
    FairPrice = Baseline + w_forecast * (Forecast - Baseline)

Spread:
    spread = clamp(0.03 + 0.5*volatility_30d + 0.1*(1 - reliability/100), 0.02, 0.15)

Range:
    Lower = FairPrice * (1 - spread)
    Upper = FairPrice * (1 + spread)

All values in ₹/kg. Mandi source data is ₹/quintal — converted at ingestion
boundary (Section 15.4). No double-counting: weather/demand/regional enter
exactly once as model regressors.
"""
from __future__ import annotations

import math


def calculate_fair_price(
    baseline: float,
    forecast: float | None,
    w_forecast: float = 0.5,
) -> float:
    """
    Section 15 corrected formula.

    If forecast is None (baseline-only mode), FairPrice == Baseline.
    """
    if forecast is None:
        return round(float(baseline), 2)
    fair = float(baseline) + float(w_forecast) * (float(forecast) - float(baseline))
    return round(fair, 2)


def calculate_spread(
    volatility_30d: float | None,
    reliability: float | None,
) -> float:
    """
    Section 15 spread formula.
    Clamped to [0.02, 0.15].

    - volatility_30d: Section 7 feature, 0-1 range (fraction, not percent).
    - reliability: 0-100 scale.
    Missing inputs default to neutral (vol=0, reliability=50).
    """
    vol = float(volatility_30d) if volatility_30d is not None else 0.0
    # Clamp volatility to [0, 1] per spec
    vol = max(0.0, min(1.0, vol))
    rel = float(reliability) if reliability is not None else 50.0
    rel = max(0.0, min(100.0, rel))

    raw = 0.03 + 0.5 * vol + 0.1 * (1 - rel / 100.0)
    spread = max(0.02, min(0.15, raw))
    return round(spread, 6)  # keep enough precision; range rounding handles display


def calculate_fair_price_range(
    fair_price: float,
    spread: float,
) -> dict:
    """
    Returns dict with lower/expected/upper in ₹/kg, rounded to 2 decimals.
    """
    fp = float(fair_price)
    sp = float(spread)
    lower = round(fp * (1 - sp), 2)
    upper = round(fp * (1 + sp), 2)
    return {
        "lower": lower,
        "expected": round(fp, 2),
        "upper": upper,
        "spread": sp,
    }


# ---------------------------------------------------------------------------
# Legacy alias for backwards-compat / test convenience
# ---------------------------------------------------------------------------
def price_discovery(
    baseline: float,
    forecast: float | None,
    volatility_30d: float | None = None,
    reliability: float | None = None,
    w_forecast: float = 0.5,
) -> dict:
    """
    Convenience: compute FairPrice + spread + range in one call.
    """
    fair = calculate_fair_price(baseline, forecast, w_forecast=w_forecast)
    spread = calculate_spread(volatility_30d, reliability)
    price_range = calculate_fair_price_range(fair, spread)
    return {
        "fair_price": fair,
        "spread": spread,
        **price_range,
    }
