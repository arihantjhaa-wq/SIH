"""
sklearn HistGradientBoostingRegressor Model for AgriDirect Pricing Engine MVP.

Implements a per-(crop, mandi) ML model trained with strict temporal validation:
- Walk-forward train/validation split (never shuffled)
- Features engineered with as_of_date discipline
- Point-in-time: train on past, validate on future
- Minimum observation threshold for training
- Baseline-only fallback for insufficient data
"""
import json
import logging
import pickle
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from app.core.db import get_db_session
from app.features.engineering import get_price_dataframe, compute_all_features
from app.features.demand import calculate_demand_index
from app.forecasting.baseline import calculate_baseline

logger = logging.getLogger(__name__)

# Configuration constants
MIN_OBSERVATIONS_FOR_TRAINING = 60  # At least 60 observations to train
VALIDATION_SPLIT_RATIO = 0.2  # Last 20% of data for validation
RANDOM_STATE = 42
MODELS_DIR = Path("models")
METADATA_FILE = "model_metadata.json"


class TemporalSplitter:
    """
    Chronological train/validation splitter for time series data.

    Preserves ordering: all training dates < all validation dates.
    Never shuffles or uses future data in training.
    """

    @staticmethod
    def split_chronological(
        df: pd.DataFrame,
        validation_ratio: float = 0.2,
        date_col: str = "price_date"
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split DataFrame chronologically by date.

        Args:
            df: DataFrame with a date column
            validation_ratio: Proportion of most recent data for validation
            date_col: Name of date column

        Returns:
            train_df, val_df where all train dates < all val dates
        """
        if df.empty:
            return df, df

        # Ensure sorted by date
        df_sorted = df.sort_values(date_col).reset_index(drop=True)

        # Calculate split index
        total = len(df_sorted)
        split_idx = int(total * (1 - validation_ratio))

        # Ensure minimum sizes
        if split_idx < MIN_OBSERVATIONS_FOR_TRAINING:
            split_idx = min(len(df_sorted), MIN_OBSERVATIONS_FOR_TRAINING)

        # Split chronologically
        train_df = df_sorted.iloc[:split_idx]
        val_df = df_sorted.iloc[split_idx:]

        # Verify ordering
        if len(train_df) > 0 and len(val_df) > 0:
            max_train_date = train_df[date_col].max()
            min_val_date = val_df[date_col].min()
            if max_train_date >= min_val_date:
                logger.warning(f"Potential date overlap: train_max={max_train_date}, val_min={min_val_date}")

        return train_df, val_df

    @staticmethod
    def get_split_dates(
        dates: List[date],
        validation_ratio: float = 0.2
    ) -> Tuple[List[date], List[date]]:
        """
        Split list of dates chronologically.
        """
        if not dates:
            return [], []

        sorted_dates = sorted(dates)
        split_idx = int(len(sorted_dates) * (1 - validation_ratio))

        train_dates = sorted_dates[:split_idx]
        val_dates = sorted_dates[split_idx:]

        return train_dates, val_dates


class ModelTrainer:
    """
    Trains and validates HistGradientBoostingRegressor per (crop, mandi) pair.
    """

    def __init__(
        self,
        commodity_id: str,
        mandi_id: str,
        random_state: int = RANDOM_STATE,
        min_obs: int = MIN_OBSERVATIONS_FOR_TRAINING
    ):
        self.commodity_id = commodity_id
        self.mandi_id = mandi_id
        self.random_state = random_state
        self.min_observations = min_obs

        self.model = None
        self.feature_names = []
        self.trained_date = None

        # Metrics
        self.training_mae = None
        self.validation_mae = None
        self.naive_baseline_mae = None
        self.baseline_only = False

        # Data counts
        self.n_train = 0
        self.n_val = 0

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features for all rows in the DataFrame.

        For each date in df, compute:
        - lag_1, rolling_mean_7, price_momentum, volatility_30d
        - demand_index (if available)
        - Baseline prediction

        Target variable: next day's modal price (y = price_{t+1})
        """
        with get_db_session() as session:
            features_list = []

            for _, row in df.iterrows():
                as_of_date = row["price_date"]

                # Get market features
                market_features = compute_all_features(
                    session, self.commodity_id, self.mandi_id, as_of_date
                )

                # Get demand index (if available)
                demand_index = calculate_demand_index(
                    session, self.commodity_id, self.mandi_id, as_of_date
                )

                # Get baseline prediction
                baseline = calculate_baseline(
                    session, self.commodity_id, self.mandi_id, as_of_date
                )

                # Get next day's price (target)
                # Look ahead one day for price
                next_day = as_of_date + timedelta(days=1)
                next_day_df = get_price_dataframe(
                    session, self.commodity_id, self.mandi_id, next_day, lookback_days=1
                )

                if not next_day_df.empty:
                    next_price = float(next_day_df.iloc[-1]["modal_price"])

                    feature_dict = {
                        "date": as_of_date,
                        "lag_1": market_features.get("lag_1"),
                        "rolling_mean_7": market_features.get("rolling_mean_7"),
                        "price_momentum_7d": market_features.get("price_momentum_7d"),
                        "volatility_30d": market_features.get("volatility_30d"),
                        "demand_index": demand_index,
                        "baseline": baseline if baseline is not None else 0.0,
                        "target_price": next_price
                    }
                    features_list.append(feature_dict)

        return pd.DataFrame(features_list)

    def prepare_training_data(
        self,
        lookback_days: int = 180
    ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Prepare train/validation data with temporal split.

        Returns:
            (train_features, val_features) or (None, None) if insufficient data
        """
        # Get raw price data
        as_of_date = date.today()
        with get_db_session() as session:
            df = get_price_dataframe(
                session, self.commodity_id, self.mandi_id,
                as_of_date, lookback_days
            )

        if len(df) < self.min_observations:
            logger.info(f"Insufficient data: {len(df)} < {self.min_observations}")
            return None, None

        # Engineer features
        feature_df = self._engineer_features(df)

        if feature_df.empty:
            return None, None

        # Split chronologically
        train_df, val_df = TemporalSplitter.split_chronological(
            feature_df, VALIDATION_SPLIT_RATIO, date_col="date"
        )

        # Check minimum sizes
        if len(train_df) < self.min_observations or len(val_df) == 0:
            logger.info(f"Insufficient split sizes: train={len(train_df)}, val={len(val_df)}")
            return None, None

        return train_df, val_df

    def train(self, train_df: pd.DataFrame) -> bool:
        """
        Train the model on prepared training data.
        """
        # Prepare feature matrix and target
        feature_cols = ["lag_1", "rolling_mean_7", "price_momentum_7d",
                       "volatility_30d", "demand_index", "baseline"]

        # Filter out rows with missing features
        train_clean = train_df.dropna(subset=feature_cols + ["target_price"])

        if len(train_clean) < self.min_observations:
            logger.warning(f"After cleaning: {len(train_clean)} < {self.min_observations}")
            return False

        X_train = train_clean[feature_cols].values
        y_train = train_clean["target_price"].values

        self.feature_names = feature_cols
        self.n_train = len(train_clean)

        # Train model
        self.model = HistGradientBoostingRegressor(
            random_state=self.random_state,
            max_iter=100,
            learning_rate=0.1,
            max_depth=5,
            verbose=0
        )

        self.model.fit(X_train, y_train)

        # Calculate training MAE
        y_train_pred = self.model.predict(X_train)
        self.training_mae = mean_absolute_error(y_train, y_train_pred)

        self.trained_date = datetime.now()

        return True

    def validate(self, val_df: pd.DataFrame) -> Dict[str, float]:
        """
        Validate model on validation data.

        Returns:
            Dictionary with ML MAE and naive baseline MAE
        """
        if self.model is None:
            return {"error": "Model not trained"}

        feature_cols = self.feature_names

        # Clean validation data
        val_clean = val_df.dropna(subset=feature_cols + ["target_price"])

        if len(val_clean) == 0:
            return {"error": "No valid validation data"}

        X_val = val_clean[feature_cols].values
        y_val = val_clean["target_price"].values

        self.n_val = len(val_clean)

        # ML prediction
        y_val_pred = self.model.predict(X_val)
        self.validation_mae = mean_absolute_error(y_val, y_val_pred)

        # Naive baseline: predict next price = current price
        # Using lag_1 as naive prediction
        naive_pred = val_clean["lag_1"].values
        self.naive_baseline_mae = mean_absolute_error(y_val, naive_pred)

        # Baseline model prediction
        baseline_pred = val_clean["baseline"].values
        baseline_mae = mean_absolute_error(y_val, baseline_pred)

        return {
            "ml_mae": self.validation_mae,
            "naive_baseline_mae": self.naive_baseline_mae,
            "baseline_mae": baseline_mae,
            "n_validation": len(val_clean)
        }

    def train_and_validate(self) -> Dict[str, Any]:
        """
        Complete training pipeline: prepare data, train, validate.

        Returns:
            Dictionary with training results
        """
        # Prepare data
        train_df, val_df = self.prepare_training_data()

        if train_df is None or val_df is None:
            self.baseline_only = True
            return {
                "status": "baseline_only",
                "reason": f"Insufficient data (needs ≥{self.min_observations} observations)",
                "commodity_id": self.commodity_id,
                "mandi_id": self.mandi_id
            }

        # Train
        success = self.train(train_df)
        if not success:
            self.baseline_only = True
            return {
                "status": "baseline_only",
                "reason": "Training failed (insufficient clean data)",
                "commodity_id": self.commodity_id,
                "mandi_id": self.mandi_id
            }

        # Validate
        metrics = self.validate(val_df)

        result = {
            "status": "trained",
            "commodity_id": self.commodity_id,
            "mandi_id": self.mandi_id,
            "n_training": self.n_train,
            "n_validation": self.n_val,
            "training_mae": float(self.training_mae),
            **metrics,
            "feature_names": self.feature_names,
            "trained_date": self.trained_date.isoformat() if self.trained_date else None,
            "model_type": "HistGradientBoostingRegressor",
            "random_state": self.random_state,
            "min_observations": self.min_observations
        }

        return result

    def save_model(self, model_path: Optional[Path] = None) -> Path:
        """
        Save model artifact and metadata.
        """
        if self.model is None:
            raise ValueError("Model not trained")

        # Create models directory
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        # Generate model filename
        if model_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = MODELS_DIR / f"model_{self.commodity_id}_{self.mandi_id}_{timestamp}.pkl"

        # Save model
        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)

        # Save metadata
        metadata = {
            "commodity_id": str(self.commodity_id),
            "mandi_id": str(self.mandi_id),
            "trained_date": self.trained_date.isoformat() if self.trained_date else None,
            "feature_names": self.feature_names,
            "training_mae": float(self.training_mae) if self.training_mae else None,
            "validation_mae": float(self.validation_mae) if self.validation_mae else None,
            "naive_baseline_mae": float(self.naive_baseline_mae) if self.naive_baseline_mae else None,
            "n_training": self.n_train,
            "n_validation": self.n_val,
            "model_type": "HistGradientBoostingRegressor",
            "random_state": self.random_state,
            "min_observations": self.min_observations,
            "baseline_only": self.baseline_only,
            "model_path": str(model_path)
        }

        metadata_path = model_path.with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return model_path

    def load_model(self, model_path: Path) -> bool:
        """
        Load a previously saved model.
        """
        try:
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)

            # Load metadata
            metadata_path = model_path.with_suffix(".json")
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

                self.commodity_id = metadata.get("commodity_id", self.commodity_id)
                self.mandi_id = metadata.get("mandi_id", self.mandi_id)
                self.feature_names = metadata.get("feature_names", [])
                self.training_mae = metadata.get("training_mae")
                self.validation_mae = metadata.get("validation_mae")
                self.baseline_only = metadata.get("baseline_only", False)

            return True
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            return False

    def predict(self, features: Dict[str, float]) -> Optional[float]:
        """
        Make prediction with trained model.

        Returns:
            Predicted price or None if model unavailable
        """
        if self.model is None or self.baseline_only:
            return None

        # Ensure all features are present
        if not all(feat in features for feat in self.feature_names):
            missing = [f for f in self.feature_names if f not in features]
            logger.warning(f"Missing features for prediction: {missing}")
            return None

        # Create feature vector
        X = np.array([[features[feat] for feat in self.feature_names]])

        try:
            prediction = float(self.model.predict(X)[0])
            return prediction
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None


def forecast_price(
    commodity_id: str,
    mandi_id: str,
    as_of_date: date,
    model_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Generate forecast for a (crop, mandi) pair.

    Returns:
        Dictionary with forecast, baseline, and metadata
    """
    with get_db_session() as session:
        # Get baseline
        baseline = calculate_baseline(session, commodity_id, mandi_id, as_of_date)

        # Get features for ML prediction
        market_features = compute_all_features(session, commodity_id, mandi_id, as_of_date)
        demand_index = calculate_demand_index(session, commodity_id, mandi_id, as_of_date)

        # Try ML prediction
        ml_prediction = None
        ml_available = False

        if model_path and model_path.exists():
            trainer = ModelTrainer(commodity_id, mandi_id)
            if trainer.load_model(model_path):
                features = {
                    "lag_1": market_features.get("lag_1", 0.0),
                    "rolling_mean_7": market_features.get("rolling_mean_7", 0.0),
                    "price_momentum_7d": market_features.get("price_momentum_7d", 0.0),
                    "volatility_30d": market_features.get("volatility_30d", 0.0),
                    "demand_index": demand_index,
                    "baseline": baseline if baseline is not None else 0.0
                }

                ml_prediction = trainer.predict(features)
                ml_available = True

    result = {
        "commodity_id": commodity_id,
        "mandi_id": mandi_id,
        "as_of_date": as_of_date.isoformat(),
        "baseline_forecast": baseline,
        "ml_forecast": ml_prediction,
        "ml_available": ml_available,
        "features": {
            **market_features,
            "demand_index": demand_index
        }
    }

    return result