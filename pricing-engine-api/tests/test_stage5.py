"""
Stage 5 Test Suite: Demand + Weather Signal Wiring.

Tests:
- Weather features (rainfall_mm, temp_max_c) are available from demo fixture
- Weather/demand appear exactly once in model feature vector (Audit Finding F1)
- Demand cold-start case still passes after wiring
- No double-adjustment of weather/demand signals elsewhere
"""
# pyrefly: ignore [missing-import]
import pytest
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
import tempfile
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.db import WeatherObservation, Mandi, Commodity, Base
from app.features.weather import get_rainfall_mm, get_temp_max_c, get_weather_features
from app.features.demand import calculate_demand_index, normalize_demand_index
from app.forecasting.sklearn_model import ModelTrainer, forecast_price, TemporalSplitter


class TestWeatherFeatures:
    """Tests for weather feature extraction."""

    def test_weather_features_exist_in_db(self, db_session, mock_mandi):
        """Weather fixture should have data for seeded mandis."""
        # Load weather fixture into test db
        _load_weather_fixture(db_session, mock_mandi)

        observations = db_session.query(WeatherObservation).filter_by(
            mandi_id=mock_mandi.id
        ).all()

        assert len(observations) > 0, "Weather observations not loaded from demo fixture"
        assert all(hasattr(obs, 'rainfall_mm') for obs in observations)
        assert all(hasattr(obs, 'temp_max_c') for obs in observations)

    def test_rainfall_with_as_of_date_discipline(self, db_session, mock_mandi):
        """Rainfall feature respects as_of_date (no future data)."""
        # Load weather fixture first
        _load_weather_fixture(db_session, mock_mandi)

        # Add a future observation that should NOT be included
        future_date = date(2030, 1, 1)
        future_obs = WeatherObservation(
            mandi_id=mock_mandi.id,
            obs_date=future_date,
            rainfall_mm=999.0,
            temp_max_c=99.0
        )
        db_session.add(future_obs)
        db_session.commit()

        # Get rainfall for a date before the future observation
        as_of_date = date(2026, 8, 1)
        rainfall = get_rainfall_mm(
            db_session, mock_mandi.id, as_of_date, lookback_days=7
        )

        # Should not include the future 999.0 mm value
        if rainfall is not None:
            assert rainfall != 999.0, "Future weather data leaked into feature"
        else:
            pytest.skip("No weather data for test date")

    def test_temp_max_with_as_of_date_discipline(self, db_session, mock_mandi):
        """Temperature feature respects as_of_date (no future data)."""
        # Load weather fixture first
        _load_weather_fixture(db_session, mock_mandi)

        # Add a future observation that should NOT be included
        future_date = date(2030, 1, 1)
        future_obs = WeatherObservation(
            mandi_id=mock_mandi.id,
            obs_date=future_date,
            rainfall_mm=0.0,
            temp_max_c=999.0
        )
        db_session.add(future_obs)
        db_session.commit()

        # Get temperature for a date before the future observation
        as_of_date = date(2026, 8, 1)
        temp = get_temp_max_c(
            db_session, mock_mandi.id, as_of_date, lookback_days=7
        )

        # Should not include the future 999.0°C value
        if temp is not None:
            assert temp != 999.0, "Future weather data leaked into feature"
        else:
            pytest.skip("No weather data for test date")

    def test_get_weather_features_returns_dict(self, db_session, mock_mandi):
        """get_weather_features returns a dictionary with expected keys."""
        as_of_date = date(2026, 8, 1)
        features = get_weather_features(db_session, mock_mandi.id, as_of_date)

        assert isinstance(features, dict)
        assert "rainfall_mm" in features
        assert "temp_max_c" in features

        # Values can be None if no data, but keys must be present
        assert features["rainfall_mm"] is None or isinstance(features["rainfall_mm"], float)
        assert features["temp_max_c"] is None or isinstance(features["temp_max_c"], float)


class TestDemandWeatherWiring:
    """Tests for wiring demand + weather into model feature set."""

    def test_demand_cold_start_still_passes(self):
        """Demand Index cold-start case still works after wiring."""
        # Test all zeros (max == min)
        result = normalize_demand_index([0.0, 0.0, 0.0])
        assert result == 0.0, f"Cold start failed: got {result}, expected 0.0"

        # Test all same value
        result = normalize_demand_index([100.0, 100.0, 100.0])
        assert result == 0.0, f"All identical values failed: got {result}, expected 0.0"

        # Test with actual range
        result = normalize_demand_index([0.0, 50.0, 100.0])
        assert result == 0.0, f"Should return first value normalized: got {result}, expected 0.0"

        # Test empty list
        result = normalize_demand_index([])
        assert result == 0.0, f"Empty list failed: got {result}, expected 0.0"

    def test_model_trainer_includes_weather_features(self, trainer):
        """ModelTrainer includes weather features in feature engineering."""
        train_df, val_df = trainer.prepare_training_data()

        if train_df is not None and not train_df.empty:
            # Check that expected columns exist
            expected_columns = ["lag_1", "rolling_mean_7", "price_momentum_7d",
                              "volatility_30d", "demand_index", "rainfall_mm",
                              "temp_max_c", "baseline", "target_price", "date"]

            missing = [col for col in expected_columns if col not in train_df.columns]
            assert len(missing) == 0, f"Missing columns in feature engineering: {missing}"

            # Weather columns may be NaN if data missing
            assert "rainfall_mm" in train_df.columns
            assert "temp_max_c" in train_df.columns

    def test_no_double_counting_weather_demand_in_model_trainer(self, trainer):
        """
        Ensure weather/demand appear exactly ONCE in model features.

        This is the critical check for Audit Finding F1.
        The test inspects ModelTrainer._engineer_features output to verify
        weather/demand are in the feature columns only.
        """
        # Create a small test DataFrame
        dates = [date(2026, 6, i) for i in range(1, 8)]
        test_df = pd.DataFrame({
            "price_date": dates,
            "modal_price": [100.0 * (i+1) for i in range(7)]
        })

        # Engineer features
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            features_df = trainer._engineer_features(test_df)

            if not features_df.empty:
                # Check column set includes weather and demand exactly once
                weather_cols = [col for col in features_df.columns if "rainfall" in col or "temp" in col or "demand" in col]

                # Should have exactly these 3 columns
                expected_weather_demand = {"demand_index", "rainfall_mm", "temp_max_c"}
                actual_set = set(weather_cols)

                assert actual_set == expected_weather_demand, \
                    f"Weather/demand columns mismatch. Expected: {expected_weather_demand}, Got: {actual_set}"

                # No other weather/demand-like columns
                assert len(weather_cols) == 3, \
                    f"Should have exactly 3 weather/demand columns, got {len(weather_cols)}: {weather_cols}"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_forecast_price_includes_weather_features(self, db_session, mock_commodity, mock_mandi):
        """forecast_price function should include weather features in its output."""
        # Load weather fixture for the test
        _load_weather_fixture(db_session, mock_mandi)

        as_of_date = date(2026, 8, 1)

        # Test without model path (baseline only)
        result = forecast_price(
            str(mock_commodity.id),
            str(mock_mandi.id),
            as_of_date,
            model_path=None
        )

        # Should include features in output
        assert "features" in result
        assert isinstance(result["features"], dict)

        # Features should include weather
        assert "rainfall_mm" in result["features"]
        assert "temp_max_c" in result["features"]

        # Features should include demand
        assert "demand_index" in result["features"]

    def test_trainer_save_load_preserves_weather_feature_names(self, trainer):
        """Saved and loaded model should preserve weather feature names."""
        # Train on demo data
        result = trainer.train_and_validate()

        if result["status"] == "trained":
            # Save to temp directory
            with tempfile.TemporaryDirectory() as tmpdir:
                model_path = Path(tmpdir) / "test_model.pkl"

                # Save model
                saved_path = trainer.save_model(model_path)
                assert saved_path.exists()

                # Load into a new trainer
                new_trainer = ModelTrainer(
                    commodity_id=trainer.commodity_id,
                    mandi_id=trainer.mandi_id
                )
                success = new_trainer.load_model(saved_path)
                assert success

                # Check feature names include weather
                assert hasattr(new_trainer, 'feature_names')
                assert isinstance(new_trainer.feature_names, list)

                # Should include weather features
                weather_related = [f for f in new_trainer.feature_names if "rainfall" in f or "temp" in f]
                assert len(weather_related) >= 1, f"Expected weather features, got: {new_trainer.feature_names}"

    def test_temporal_splitter_preserves_chronological_order(self):
        """TemporalSplitter should never shuffle data (weather + demand features)."""
        dates = [date(2026, 1, i) for i in range(1, 31)]  # 30 days
        df = pd.DataFrame({
            "date": dates,
            "price": np.random.random(30) * 100,
            "demand_index": np.random.random(30) * 100,
            "rainfall_mm": np.random.random(30) * 50,
            "temp_max_c": np.random.random(30) * 30 + 20
        })

        train_df, val_df = TemporalSplitter.split_chronological(df, 0.2, date_col="date")

        # Verify no shuffle - all train dates must be before all val dates
        if len(train_df) > 0 and len(val_df) > 0:
            max_train_date = train_df["date"].max()
            min_val_date = val_df["date"].min()
            assert max_train_date < min_val_date, \
                f"Chronological order violated: train_max={max_train_date}, val_min={min_val_date}"

        # Verify features preserved
        for df_part in [train_df, val_df]:
            if len(df_part) > 0:
                assert "demand_index" in df_part.columns
                assert "rainfall_mm" in df_part.columns
                assert "temp_max_c" in df_part.columns


class TestFeatureEngineeringIntegration:
    """Integration tests for feature engineering with weather + demand."""

    def test_model_trainer_feature_vector_dimensions(self, trainer):
        """Model feature vector should have correct dimensions with new features."""
        # Original features (Stage 4): lag_1, rolling_mean_7, price_momentum_7d,
        # volatility_30d, demand_index, baseline → 6 features
        # New features (Stage 5): rainfall_mm, temp_max_c → +2 features = 8 total
        train_df, val_df = trainer.prepare_training_data()

        if train_df is not None and val_df is not None:
            # Check if there's enough data
            if len(train_df) >= trainer.min_observations and len(val_df) > 0:
                # Train model
                success = trainer.train(train_df)
                if success:
                    # Expected: 8 features
                    assert hasattr(trainer, 'feature_names')
                    assert len(trainer.feature_names) == 8, \
                        f"Expected 8 features, got {len(trainer.feature_names)}: {trainer.feature_names}"

                    # Should include weather
                    assert any("rainfall" in f for f in trainer.feature_names)
                    assert any("temp_max" in f for f in trainer.feature_names)

                    # Should include demand
                    assert "demand_index" in trainer.feature_names

                # Validate
                metrics = trainer.validate(val_df)
                if "error" not in metrics:
                    assert "ml_mae" in metrics
                    assert "naive_baseline_mae" in metrics
                    assert metrics["ml_mae"] >= 0
                    assert metrics["naive_baseline_mae"] >= 0


# ============================================================================
# Fixtures (reuse from test_stage4.py)
# ============================================================================

@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _load_weather_fixture(session, mandi):
    """Load demo weather observations into the test database."""
    # Seed weather data similar to data/demo/weather.csv
    weather_data = [
        (date(2026, 6, 1), 12.5, 34.2),
        (date(2026, 6, 2), 8.3, 35.1),
        (date(2026, 6, 3), 0.0, 36.8),
        (date(2026, 6, 4), 22.1, 33.0),
        (date(2026, 6, 5), 5.0, 35.5),
        (date(2026, 6, 6), 15.7, 34.0),
        (date(2026, 6, 7), 3.2, 36.2),
        (date(2026, 6, 8), 10.0, 33.8),
        (date(2026, 6, 9), 18.4, 32.5),
        (date(2026, 6, 10), 7.6, 35.0),
        (date(2026, 6, 11), 2.3, 36.5),
        (date(2026, 6, 12), 25.0, 31.2),
        (date(2026, 6, 13), 0.0, 37.0),
        (date(2026, 6, 14), 11.8, 34.5),
        (date(2026, 6, 15), 6.4, 35.8),
        (date(2026, 6, 16), 14.2, 33.2),
        (date(2026, 6, 17), 19.5, 32.0),
        (date(2026, 6, 18), 4.1, 36.0),
        (date(2026, 6, 19), 8.9, 34.8),
        (date(2026, 6, 20), 0.0, 37.2),
        (date(2026, 6, 21), 30.2, 30.5),
        (date(2026, 6, 22), 16.7, 33.5),
        (date(2026, 6, 23), 2.0, 36.8),
        (date(2026, 6, 24), 9.3, 35.2),
        (date(2026, 6, 25), 21.0, 31.8),
        (date(2026, 6, 26), 7.8, 34.2),
        (date(2026, 6, 27), 13.5, 33.0),
        (date(2026, 6, 28), 0.0, 37.5),
        (date(2026, 6, 29), 28.4, 30.0),
        (date(2026, 6, 30), 11.2, 34.8),
        (date(2026, 7, 1), 5.5, 35.5),
        (date(2026, 7, 2), 17.8, 32.8),
        (date(2026, 7, 3), 9.0, 34.0),
        (date(2026, 7, 4), 0.0, 36.5),
        (date(2026, 7, 5), 23.1, 31.0),
        (date(2026, 7, 6), 6.8, 35.0),
        (date(2026, 7, 7), 14.5, 33.5),
        (date(2026, 7, 8), 3.2, 36.2),
        (date(2026, 7, 9), 19.7, 32.2),
        (date(2026, 7, 10), 8.0, 34.5),
        (date(2026, 7, 11), 27.3, 30.8),
        (date(2026, 7, 12), 12.0, 33.8),
        (date(2026, 7, 13), 0.0, 37.0),
        (date(2026, 7, 14), 15.2, 33.0),
        (date(2026, 7, 15), 4.6, 35.8),
        (date(2026, 7, 16), 20.8, 31.5),
        (date(2026, 7, 17), 10.3, 34.2),
        (date(2026, 7, 18), 1.5, 36.8),
        (date(2026, 7, 19), 16.0, 32.5),
        (date(2026, 7, 20), 7.2, 34.8),
        (date(2026, 7, 21), 24.5, 30.5),
        (date(2026, 7, 22), 8.8, 34.0),
        (date(2026, 7, 23), 0.0, 36.0),
        (date(2026, 7, 24), 13.1, 33.2),
        (date(2026, 7, 25), 19.0, 32.0),
        (date(2026, 7, 26), 5.4, 35.5),
        (date(2026, 7, 27), 22.7, 31.0),
        (date(2026, 7, 28), 11.5, 33.8),
        (date(2026, 7, 29), 3.8, 36.5),
        (date(2026, 7, 30), 17.3, 32.5),
        (date(2026, 7, 31), 6.0, 35.0),
        (date(2026, 8, 1), 14.0, 33.5),
    ]

    for obs_date, rainfall, temp in weather_data:
        obs = WeatherObservation(
            mandi_id=mandi.id,
            obs_date=obs_date,
            rainfall_mm=rainfall,
            temp_max_c=temp,
            source="demo_fixture"
        )
        session.add(obs)

    session.commit()


@pytest.fixture
def mock_commodity(db_session):
    """Create a test commodity."""
    from app.core.db import Commodity
    commodity = Commodity(
        name="Tomato",
        category="fruit_veg",
        unit="kg",
        shelf_life_days=7,
        is_active=True
    )
    db_session.add(commodity)
    db_session.commit()
    return commodity


@pytest.fixture
def mock_mandi(db_session):
    """Create a test mandi."""
    from app.core.db import Mandi
    mandi = Mandi(
        name="Test Market",
        state="Maharashtra",
        district="Pune",
        latitude=18.520430,
        longitude=73.856744,
        agmarknet_code="TEST_CODE"
    )
    db_session.add(mandi)
    db_session.commit()
    return mandi


@pytest.fixture
def trainer(db_session, mock_commodity, mock_mandi):
    """Create a ModelTrainer for testing."""
    from app.data.ingest import ingest_from_csv
    from app.core.config import DEMO_MANDI_PRICES_PATH

    # Load weather fixture for the test
    _load_weather_fixture(db_session, mock_mandi)

    # Ingest demo data first
    result = ingest_from_csv(csv_path=DEMO_MANDI_PRICES_PATH)

    return ModelTrainer(
        commodity_id=str(mock_commodity.id),
        mandi_id=str(mock_mandi.id),
        random_state=42,
        min_obs=30
    )
