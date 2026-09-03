"""
Deterministic Baseline Model for AgriDirect Pricing Engine.

Implements the frozen specification's baseline formula:
Baseline(t) = 0.4 × ModalPrice(t-1) + 0.3 × WMA(7d) + 0.2 × RegionalMedian(state, commodity, t-1) + 0.1 × SeasonalIndex

WMA must use exponential weights: weight_i = 0.9^i
"""
from datetime import date, timedelta
from typing import Optional, List
import numpy as np
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.db import MandiPrice, Commodity, Mandi
from app.features.engineering import lag_1, rolling_mean_7


def wma_7d(prices: List[float]) -> float:
    """
    Weighted Moving Average with exponential weights for 7 days.

    weight_i = 0.9^i where i=0 is the most recent price (t-1)
    The weights decay from most recent to oldest.

    Prices should be ordered from oldest to newest.
    """
    if len(prices) < 7:
        raise ValueError("WMA requires at least 7 price points")

    # Use the last 7 prices (ordered oldest -> newest)
    last_7_prices = prices[-7:]

    # Exponential weights: weight_i = 0.9^i
    # i=0 is most recent (newest price), so weights must be assigned
    # in reverse: oldest price gets 0.9^6, newest gets 0.9^0 = 1.0
    # Build weights in price order: [0.9^6, 0.9^5, ..., 0.9^1, 0.9^0]
    weights = np.array([0.9 ** i for i in range(6, -1, -1)])

    # Normalize weights to sum to 1
    normalized_weights = weights / weights.sum()

    # Calculate weighted average
    wma = np.dot(last_7_prices, normalized_weights)

    return float(wma)


def get_regional_median(
    session: Session,
    state: str,
    commodity_id: str,
    as_of_date: date
) -> Optional[float]:
    """
    Calculate the regional median price for a state/commodity as of the previous trading day.
    """
    # Get data for the previous day
    prev_day = as_of_date - timedelta(days=1)

    # Find all mandis in the state
    mandis = session.query(Mandi.id).filter(Mandi.state == state).all()
    mandi_ids = [m.id for m in mandis]

    if not mandi_ids:
        return None

    # Get modal prices for the previous day
    prices = session.query(MandiPrice.modal_price).filter(
        and_(
            MandiPrice.commodity_id == commodity_id,
            MandiPrice.mandi_id.in_(mandi_ids),
            MandiPrice.price_date == prev_day,
            MandiPrice.is_flagged_outlier == False
        )
    ).all()

    if not prices:
        return None

    # Convert to float list
    price_values = [float(p[0]) for p in prices if p[0] is not None]

    if not price_values:
        return None

    # Calculate median
    median_price = float(np.median(price_values))
    return median_price


def get_seasonal_index(
    commodity_id: str,
    as_of_date: date
) -> float:
    """
    Get seasonal index for a commodity at a specific date.

    MVP Implementation: Returns 1.0 (no seasonality) for all commodities.
    In full implementation, this would be based on historical seasonal patterns.

    Note: This returns a multiplier that should be applied to the baseline,
    not an additive value. The formula treats it as a multiplier.
    """
    # MVP stub: no seasonal adjustment
    return 1.0


def calculate_baseline(
    session: Session,
    commodity_id: str,
    mandi_id: str,
    as_of_date: date
) -> Optional[float]:
    """
    Calculate the deterministic baseline for a commodity/mandi/date.

    Formula:
    Baseline(t) = 0.4 × ModalPrice(t-1) + 0.3 × WMA(7d) + 0.2 × RegionalMedian(state, commodity, t-1) + 0.1 × SeasonalIndex

    Returns None if insufficient data to calculate any component.
    """
    # Get individual components
    modal_price_lag_1 = lag_1(session, commodity_id, mandi_id, as_of_date)

    # Get data for WMA
    from app.features.engineering import get_price_dataframe
    df = get_price_dataframe(session, commodity_id, mandi_id, as_of_date, lookback_days=10)

    # Get regional median
    mandi = session.query(Mandi).filter(Mandi.id == mandi_id).first()
    if not mandi:
        return None

    regional_median = get_regional_median(session, mandi.state, commodity_id, as_of_date)

    # Get seasonal index
    seasonal_idx = get_seasonal_index(commodity_id, as_of_date)

    # Check if we have enough data
    components = [modal_price_lag_1, regional_median]

    # For WMA, we need at least 7 prices
    if len(df) < 7:
        return None

    # Convert prices to list for WMA
    price_list = df['modal_price'].tolist()

    try:
        wma_value = wma_7d(price_list)
    except ValueError:
        return None

    # If any essential component is missing, return None
    if modal_price_lag_1 is None or regional_median is None:
        return None

    # Apply weights
    baseline_value = (
        0.4 * modal_price_lag_1 +
        0.3 * wma_value +
        0.2 * regional_median +
        0.1 * seasonal_idx
    )

    return baseline_value


def get_last_n_prices(
    session: Session,
    commodity_id: str,
    mandi_id: str,
    as_of_date: date,
    n: int = 7
) -> List[float]:
    """
    Get the last n modal prices up to as_of_date for WMA calculation.
    """
    from app.features.engineering import get_price_dataframe

    df = get_price_dataframe(session, commodity_id, mandi_id, as_of_date, lookback_days=n+3)

    if df.empty:
        return []

    # Get the last n prices
    last_n = df.tail(n)['modal_price'].tolist()

    return last_n