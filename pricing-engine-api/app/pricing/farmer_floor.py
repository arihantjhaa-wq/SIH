"""
Farmer Protection Floor — Section 17.

FLOOR = max( 0.85 × Baseline, FarmerDeclaredMinimum_if_set )

If FairPrice.Lower < FLOOR:
    → status = "BLOCKED"
    → reason = "recommended price X% below baseline floor"

The floor is a **hard constraint**, not a signal. It blocks/flags below-threshold
recommendations.
"""
from __future__ import annotations

from typing import Literal


FLOOR_TOLERANCE = 0.85  # 15% tolerance band per spec assumption


def calculate_farmer_floor(
    baseline: float,
    farmer_declared_minimum: float | None = None,
    floor_tolerance: float = FLOOR_TOLERANCE,
) -> float:
    """
    Section 17 floor formula.

    Args:
        baseline: Baseline price in ₹/kg (Section 8).
        farmer_declared_minimum: Optional farmer's own minimum price.
        floor_tolerance: Fraction of baseline to use (default 0.85).

    Returns:
        Floor price in ₹/kg, rounded to 2 decimals.
    """
    baseline_floor = float(baseline) * float(floor_tolerance)
    baseline_floor = round(baseline_floor, 2)

    if farmer_declared_minimum is not None:
        declared = float(farmer_declared_minimum)
        declared = round(declared, 2)
        return max(baseline_floor, declared)

    return baseline_floor


def check_floor_protection(
    fair_price_lower: float,
    floor: float,
) -> dict:
    """
    Check if FairPrice.Lower satisfies the farmer protection constraint.

    Args:
        fair_price_lower: Lower bound of the fair price range.
        floor: Calculated farmer protection floor.

    Returns:
        {
            "blocked": bool,                # True if below floor
            "status": "OK"|"BLOCKED",
            "reason": str | None,
            "floor": float,
            "margin_above_floor": float,   # Positive if OK, negative if blocked
            "percent_below_floor": float,  # |margin/floor|*100 if blocked
        }
    """
    lower = float(fair_price_lower)
    fl = float(floor)
    margin = round(lower - fl, 2)

    if margin >= 0:
        return {
            "blocked": False,
            "status": "OK",
            "reason": None,
            "floor": fl,
            "margin_above_floor": margin,
            "percent_below_floor": 0.0,
        }

    pct_below = round(abs(margin) / fl * 100.0, 2)
    return {
        "blocked": True,
        "status": "BLOCKED",
        "reason": f"recommended price {pct_below}% below baseline floor",
        "floor": fl,
        "margin_above_floor": margin,
        "percent_below_floor": pct_below,
    }


def apply_floor_check(
    fair_price_range: dict,
    baseline: float,
    farmer_declared_minimum: float | None = None,
) -> dict:
    """
    Convenience: run full floor check and merge into price range result.

    Args:
        fair_price_range: Result from calculate_fair_price_range().
        baseline: Baseline price in ₹/kg.
        farmer_declared_minimum: Optional farmer's declared minimum.

    Returns:
        fair_price_range extended with floor fields:
        {
            "lower", "expected", "upper", "spread",
            "floor", "floor_blocked", "floor_margin", "floor_pct_below",
            "floor_reason",
        }
    """
    floor = calculate_farmer_floor(baseline, farmer_declared_minimum)
    check = check_floor_protection(fair_price_range["lower"], floor)

    result = dict(fair_price_range)
    result["floor"] = floor
    result["floor_blocked"] = check["blocked"]
    result["floor_margin"] = check["margin_above_floor"]
    result["floor_pct_below"] = check["percent_below_floor"]
    result["floor_reason"] = check["reason"]

    return result
