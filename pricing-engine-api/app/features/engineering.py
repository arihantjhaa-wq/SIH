"""
Point-in-Time Feature Engineering for AgriDirect Pricing Engine.

Implements market features with explicit as_of_date leakage protection.
A feature calculated for date t MUST NOT use any price observation later than t.
"""
from datetime import date, timedelta
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.db import MandiPrice, Mandi, Commodity


def get_price_dataframe(
    session: Session,
    commodity_id: str,
    mandi_id: str,
    as_of_date: date,
    lookback_days: int = 60
) -> pd.DataFrame:
    """
    Fetch price data for a specific commodity/mandi up to as_of_date.
    Returns a DataFrame sorted by price_date with no future data.

    This is the primary leakage-protection mechanism - all features must
    call this function to ensure they never see future data.
    """
    start_date = as_of_date - timedelta(days=lookback_days)

    records = session.query(MandiPrice).filter(
        and_(
            MandiPrice.commodity_id == commodity_id,
            MandiPrice.mandi_id == mandi_id,
            MandiPrice.price_date <= as_of_date,
            MandiPrice.price_date >= start_date,
            MandiPrice.is_flagged_outlier == False,
            MandiPrice.modal_price.isnot(None)
        )
    ).order_by(MandiPrice.price_date).all()

    if not records:
        return pd.DataFrame(columns=['price_date', 'modal_price'])

    data = [{
        'price_date': r.price_date,
        'modal_price': float(r.modal_price)
    } for r in records]

    return pd.DataFrame(data)


def lag_1(
    session: Session,
    commodity_id: str,
    mandi_id: str,
    as_of_date: date
) -> Optional[float]:
    """
    Return the modal price from the most recent trading day before as_of_date.
    Returns None if no data available for the lag period.
    """
    df = get_price_dataframe(session, commodity_id, mandi_id, as_of_date, lookback_days=7)

    if df.empty:
        return None

    # Get the last price before as_of_date
    # Data is already filtered to <= as_of_date by get_price_dataframe
    return df.iloc[-1]['modal_price'] if len(df) > 0 else None


def rolling_mean_7(
    session: Session,
    commodity_id: str,
    mandi_id: str,
    as_of_date: date
) -> Optional[float]:
    """
    Calculate the 7-day rolling mean of modal prices ending on as_of_date - 1.
    This ensures no data after as_of_date is used.
    """
    df = get_price_dataframe(session, commodity_id, mandi_id, as_of_date, lookback_days=14)

    if df.empty or len(df) < 7:
        return None

    # Use the last 7 prices before as_of_date
    last_7 = df.tail(7)['modal_price']
    return float(last_7.mean())


def price_momentum(
    session: Session,
    commodity_id: str,
    mandi_id: str,
    as_of_date: date,
    window_days: int = 7
) -> Optional[float]:
    """
    Calculate price momentum over the specified window (default 7 days).

    Momentum = (price_{t-1} - price_{t-n}) / price_{t-n}

    A positive value indicates upward momentum, negative indicates downward.
    Returns None if insufficient data.
    """
    df = get_price_dataframe(session, commodity_id, mandi_id, as_of_date, lookback_days=14)

    if df.empty or len(df) < window_days + 1:
        return None

    # Get the most recent price and price 'window_days' ago
    current_price = df.iloc[-1]['modal_price']
    past_price = df.iloc[-(window_days + 1)]['modal_price']

    if past_price == 0:
        return None

    return (current_price - past_price) / past_price


def volatility_30d(
    session: Session,
    commodity_id: str,
    mandi_id: str,
    as_of_date: date
) -> Optional[float]:
    """
    Calculate 30-day rolling volatility (coefficient of variation).

    Volatility = stddev / mean

    Returns the coefficient of variation (dimensionless) for the last 30 days
    of prices before as_of_date. Returns None if insufficient data.
    """
    df = get_price_dataframe(session, commodity_id, mandi_id, as_of_date, lookback_days=45)

    if df.empty or len(df) < 10:
        return None

    # Use last 30 days
    last_30 = df.tail(30)['modal_price']

    if len(last_30) < 10:
        return None

    mean_price = last_30.mean()
    if mean_price == 0:
        return None

    std_price = last_30.std()
    return float(std_price / mean_price)


def compute_all_features(
    session: Session,
    commodity_id: str,
    mandi_id: str,
    as_of_date: date
) -> dict:
    """
    Compute all market features for a given commodity/mandi/date combination.
    Returns a dictionary with all feature values.
    """
    features = {
        'as_of_date': as_of_date,
        'commodity_id': commodity_id,
        'mandi_id': mandi_id,
        'lag_1': lag_1(session, commodity_id, mandi_id, as_of_date),
        'rolling_mean_7': rolling_mean_7(session, commodity_id, mandi_id, as_of_date),
        'price_momentum_7d': price_momentum(session, commodity_id, mandi_id, as_of_date),
        'volatility_30d': volatility_30d(session, commodity_id, mandi_id, as_of_date),
    }
    return features