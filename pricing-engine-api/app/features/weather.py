"""
Weather Features for AgriDirect Pricing Engine.

Implements rainfall_mm and temp_max_c features with as_of_date discipline
(point-in-time, no data leakage).
"""
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.core.db import WeatherObservation


def get_rainfall_mm(
    session: Session,
    mandi_id: str,
    as_of_date: date,
    lookback_days: int = 7
) -> Optional[float]:
    """
    Get average rainfall (mm) for the past N days, up to and including as_of_date.

    Point-in-time safe: only uses observations with obs_date <= as_of_date.
    """
    if not mandi_id or not as_of_date:
        return None

    start_date = as_of_date - timedelta(days=lookback_days)

    observations = session.query(WeatherObservation).filter(
        WeatherObservation.mandi_id == mandi_id,
        WeatherObservation.obs_date >= start_date,
        WeatherObservation.obs_date <= as_of_date  # No future data
    ).all()

    if not observations:
        return None

    rainfall_values = [
        float(obs.rainfall_mm) for obs in observations
        if obs.rainfall_mm is not None
    ]

    if not rainfall_values:
        return None

    return sum(rainfall_values) / len(rainfall_values)


def get_temp_max_c(
    session: Session,
    mandi_id: str,
    as_of_date: date,
    lookback_days: int = 7
) -> Optional[float]:
    """
    Get average max temperature (°C) for the past N days, up to and including as_of_date.

    Point-in-time safe: only uses observations with obs_date <= as_of_date.
    """
    if not mandi_id or not as_of_date:
        return None

    start_date = as_of_date - timedelta(days=lookback_days)

    observations = session.query(WeatherObservation).filter(
        WeatherObservation.mandi_id == mandi_id,
        WeatherObservation.obs_date >= start_date,
        WeatherObservation.obs_date <= as_of_date  # No future data
    ).all()

    if not observations:
        return None

    temp_values = [
        float(obs.temp_max_c) for obs in observations
        if obs.temp_max_c is not None
    ]

    if not temp_values:
        return None

    return sum(temp_values) / len(temp_values)


def get_weather_features(
    session: Session,
    mandi_id: str,
    as_of_date: date,
    lookback_days: int = 7
) -> dict:
    """
    Get all weather features as a dictionary.

    Returns:
        {
            "rainfall_mm": float or None,
            "temp_max_c": float or None
        }
    """
    return {
        "rainfall_mm": get_rainfall_mm(session, mandi_id, as_of_date, lookback_days),
        "temp_max_c": get_temp_max_c(session, mandi_id, as_of_date, lookback_days),
    }
