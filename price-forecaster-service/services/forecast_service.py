"""
Core forecasting service — train model and generate 7-day price predictions.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from typing import Dict, List, Tuple, Optional
from config import settings


class ForecastError(Exception):
    """Forecasting operation failed."""
    pass


class ForecastService:
    """Train model and generate price forecasts."""

    @staticmethod
    def generate_forecast(
        historical_prices: Optional[pd.DataFrame],
        historical_weather: pd.DataFrame,
        forecast_weather: pd.DataFrame,
        commodity: str,
        state: str
    ) -> Dict:
        """
        Generate 7-day price forecast.

        Args:
            historical_prices: DataFrame with date and modal_price_inr (may be None)
            historical_weather: DataFrame with date, max_temp, rainfall_mm
            forecast_weather: DataFrame with date, max_temp, rainfall_mm
            commodity: Commodity name
            state: State name

        Returns:
            {
                "forecast": [{"date": "...", "predicted_price_inr_per_kg": ..., ...}],
                "data_source": "model" or "fallback",
                "trend": {"direction": "...", "change_percent": ...}
            }
        """
        try:
            # Build training dataset
            train_df, source = ForecastService._build_training_data(
                historical_prices,
                historical_weather,
                commodity,
                state
            )

            # Add temporal features
            train_df["day_of_week"] = train_df["date"].dt.dayofweek
            train_df["is_weekend"] = train_df["day_of_week"].isin([5, 6]).astype(int)

            # Train model
            features = ["max_temp", "rainfall_mm", "day_of_week", "is_weekend"]
            model = RandomForestRegressor(
                n_estimators=settings.RF_N_ESTIMATORS,
                random_state=settings.RF_RANDOM_STATE,
                n_jobs=-1
            )
            model.fit(train_df[features], train_df["modal_price_inr"])

            # Prepare forecast features
            forecast_weather["day_of_week"] = forecast_weather["date"].dt.dayofweek
            forecast_weather["is_weekend"] = (
                forecast_weather["day_of_week"].isin([5, 6]).astype(int)
            )

            # Predict
            predictions = model.predict(forecast_weather[features])
            forecast_weather["predicted_price_inr"] = np.round(predictions, 2)

            # Calculate trend
            first_price = float(forecast_weather.iloc[0]["predicted_price_inr"])
            last_price = float(forecast_weather.iloc[-1]["predicted_price_inr"])
            change_pct = ((last_price - first_price) / first_price) * 100

            direction = ForecastService._classify_trend(change_pct)

            # Build response
            forecast_list = []
            for _, row in forecast_weather.iterrows():
                forecast_list.append({
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "predicted_price_inr_per_kg": float(row["predicted_price_inr"]),
                    "rainfall_mm": float(row["rainfall_mm"]),
                    "temperature_c": float(row["max_temp"])
                })

            return {
                "forecast": forecast_list,
                "data_source": source,
                "trend": {
                    "direction": direction,
                    "change_percent": round(change_pct, 2),
                    "first_price_inr": first_price,
                    "last_price_inr": last_price
                }
            }

        except Exception as e:
            raise ForecastError(f"Forecast generation failed: {e}")

    @staticmethod
    def _build_training_data(
        historical_prices: Optional[pd.DataFrame],
        historical_weather: pd.DataFrame,
        commodity: str,
        state: str
    ) -> Tuple[pd.DataFrame, str]:
        """
        Build training dataset from historical data.

        Returns:
            (training_df, data_source_label)
        """
        # Try to merge price and weather data
        if historical_prices is not None and not historical_prices.empty:
            # Merge on date
            merged = pd.merge(
                historical_weather,
                historical_prices,
                on="date",
                how="inner"
            )

            if len(merged) >= 3:
                print(
                    f"[Forecast] Using {len(merged)} days of merged "
                    f"price+weather data"
                )
                return merged, "model"
            else:
                print(
                    f"[Forecast] Only {len(merged)} overlapping days; "
                    f"using blended fallback"
                )

        # Fallback: synthetic prices from weather + fixed coefficient
        print("[Forecast] Using deterministic fallback pricing")
        train_df = historical_weather.copy()
        train_df["modal_price_inr"] = (
            settings.BASE_PRICE_INR +
            (train_df["rainfall_mm"] * settings.RAINFALL_COEFFICIENT)
        )

        return train_df, "fallback"

    @staticmethod
    def _classify_trend(change_percent: float) -> str:
        """
        Classify trend based on percentage change.

        Args:
            change_percent: Percentage change from first to last day

        Returns:
            "rising", "falling", or "stable"
        """
        threshold = settings.STABLE_THRESHOLD

        if change_percent > threshold:
            return "rising"
        elif change_percent < -threshold:
            return "falling"
        else:
            return "stable"
