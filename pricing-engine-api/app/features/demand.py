"""
Demand Index Calculation for AgriDirect Pricing Engine.

Implements the MVP Demand Index using order_count_7d and requested_qty_7d,
with corrected normalization that handles cold-start (all zeros) gracefully.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from decimal import Decimal
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.db import DemandSignal, Commodity, Mandi


def get_demand_signals(
    session: Session,
    commodity_id: str,
    region_id: str,
    as_of_date: datetime,
    lookback_days: int = 7
) -> list[DemandSignal]:
    """
    Fetch demand signals for a commodity/region up to as_of_date.
    """
    start_time = as_of_date - timedelta(days=lookback_days)

    signals = session.query(DemandSignal).filter(
        and_(
            DemandSignal.commodity_id == commodity_id,
            DemandSignal.region_id == region_id,
            DemandSignal.window_end <= as_of_date,
            DemandSignal.window_start >= start_time
        )
    ).order_by(DemandSignal.window_end.desc()).all()

    return signals


def normalize_demand_index(values: list[float]) -> float:
    """
    Normalize demand values to 0-100 scale using min-max normalization.

    CRITICAL: Implements the cold-start fix from the audit:
    norm(x) = 0 when max == min (including all-zero case).
    Never divides by zero.
    """
    if not values:
        return 0.0

    min_val = min(values)
    max_val = max(values)

    # Cold-start fix: if all values are identical (including all zeros)
    if max_val == min_val:
        return 0.0

    # Normal min-max normalization
    range_val = max_val - min_val
    if range_val == 0:
        return 0.0

    # Normalize each value and return the most recent one
    normalized = [(v - min_val) / range_val * 100.0 for v in values]
    return normalized[0] if normalized else 0.0


def calculate_demand_index(
    session: Session,
    commodity_id: str,
    region_id: str,
    as_of_date: datetime
) -> float:
    """
    Calculate the Demand Index for a commodity/region at a specific point in time.

    Uses two signals from the 7-day window:
    1. order_count_7d - total orders in the window
    2. requested_qty_7d - total requested quantity in kg

    Returns a normalized 0-100 value where:
    - 0 means no/little demand (cold start or minimum)
    - 100 means maximum demand relative to historical range
    """
    signals = get_demand_signals(session, commodity_id, region_id, as_of_date)

    if not signals:
        return 0.0

    # Extract raw signals
    order_counts = [float(s.order_count) for s in signals]
    requested_qtys = [float(s.requested_qty_kg) for s in signals]

    # Aggregate the window (sum across all signals in the 7-day window)
    total_orders = sum(order_counts) if order_counts else 0.0
    total_qty = sum(requested_qtys) if requested_qtys else 0.0

    # Simple aggregation for MVP: use the total orders as the primary signal
    # Normalize against a reasonable maximum (e.g., 100 orders = max demand)
    # In production, this would be learned from historical data
    max_possible_orders = 100.0

    if max_possible_orders == 0:
        return 0.0

    order_index = min(total_orders / max_possible_orders, 1.0) * 100.0

    # For quantity-based signal, normalize against a reasonable max
    # In MVP, we use a simple heuristic: 10000 kg = max demand
    max_possible_qty = 10000.0

    if max_possible_qty == 0:
        qty_index = 0.0
    else:
        qty_index = min(total_qty / max_possible_qty, 1.0) * 100.0

    # Weighted average: 60% order count, 40% quantity
    demand_index = 0.6 * order_index + 0.4 * qty_index

    return demand_index


def get_demand_signals_for_normalization(
    session: Session,
    commodity_id: str,
    region_id: str,
    historical_window_days: int = 30,
    as_of_date: datetime = None
) -> list[Tuple[int, float]]:
    """
    Fetch historical demand signals for min-max normalization.
    Returns list of (days_ago, normalized_value) tuples.
    """
    if as_of_date is None:
        as_of_date = datetime.now()

    signals = session.query(DemandSignal).filter(
        and_(
            DemandSignal.commodity_id == commodity_id,
            DemandSignal.region_id == region_id,
            DemandSignal.window_end <= as_of_date,
            DemandSignal.window_end >= as_of_date - timedelta(days=historical_window_days)
        )
    ).order_by(DemandSignal.window_end).all()

    result = []
    for signal in signals:
        days_ago = (as_of_date - signal.window_end).days
        # Simple metric: order count normalized
        value = float(signal.order_count)
        result.append((days_ago, value))

    return result