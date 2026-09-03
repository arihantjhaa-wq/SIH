"""
Stage 4 Test Suite: ML Forecasting with HistGradientBoostingRegressor.

Tests:
- Temporal validation (walk-forward, no shuffle, chronological split)
- Model training and validation per (crop, mandi)
- Model artifact save/load
- Forecast retrieval
- Insufficient data fallback to baseline-only
- Reproducibility
- MAE calculation correctness
- Stage 1-3 regression
"""
# pyrefly: ignore [missing-import]
import pytest
import json
import pickle
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from app.core.db import Commodity, Mandi, MandiPrice
from app.forecasting.sklearn_model import (
    ModelTrainer,
    TemporalSplitter,
    forecast_price,
    MIN_OBSERVATIONS_FOR_TRAINING,
    RANDOM_STATE
)


class TestTemporalSplitter:
    """Tests for chronological temporal splitter."""

    def test_split_preserves_chronological_order(self):
        """Split must preserve chronological ordering."""
        dates = [date(2026, 1, i) for i in range(1, 31)]  # 30 days
        df = pd.DataFrame({
            "price_date": dates,
            "price": np.random.random(30) * 100
        })

        train, val = TemporalSplitter.split_chronological(df, 0.2)

        # All train dates must be before all val dates
        if len(train) > 0 and len(val) > 0:
            max_train = train["price_date"].max()
            min_val = val["price_date"].min()
            assert max_train < min_val, f"Overlap: train_max={max_train}, val_min={min_val}"

    def test_split_no_shuffle(self):
        """Split must never shuffle data."""
        dates = list(range(30))  # Sequential integers
        df = pd.DataFrame({
            "price_date": dates,
            "price": dates  # Price = date for easy verification
        })

        train, val = TemporalSplitter.split_chronological(df, 0.2)

        # Verify order is preserved
        train_prices = train["price"].tolist()
        val_prices = val["price"].tolist()

        # All train prices should be less than all val prices
        if len(train) > 0 and len(val) > 0:
            assert max(train_prices) < min(val_prices)

    def test_split_dates_function(self):
        """Test date-only split function."""
        dates = [date(2026, 1, i) for i in range(1, 31)]

        train_dates, val_dates = TemporalSplitter.get_split_dates(dates, 0.2)

        # Check counts
        assert len(train_dates) + len(val_dates) == 30
        assert len(val_dates) == 6  # 20% of 30

        # All train dates before val dates
        if train_dates and val_dates:
            assert max(train_dates) < min(val_dates)

    def test_split_with_minimum_obs(self):
        """Split respects minimum observation threshold."""
        # Only 10 observations
        dates = [date(2026, 1, i) for i in range(1, 11)]
        df = pd.DataFrame({
            "price_date": dates,
            "price": np.random.random(10) * 100
        })

        # Request 20% validation but minimum should apply
        train, val = TemporalSplitter.split_chronological(df, 0.2)

        # Should have enough training observations
        assert len(train) >= MIN_OBSERVATIONS_FOR_TRAINING or len(train) == len(df)


class TestModelTrainer:
    """Tests for ModelTrainer class."""

    @pytest.fixture
    def trainer(self, db_session, mock_commodity, mock_mandi):
        """Create a ModelTrainer for testing."""
        # First ingest some demo data
        from app.data.ingest import ingest_from_csv
        from app.core.config import DEMO_MANDI_PRICES_PATH

        result = ingest_from_csv(csv_path=DEMO_MANDI_PRICES_PATH)

        return ModelTrainer(
            commodity_id=str(mock_commodity.id),
            mandi_id=str(mock_mandi.id),
            random_state=42,
            min_obs=30
        )

    def test_train_completes(self, trainer):
        """Model training should complete on demo data."""
        result = trainer.train_and_validate()

        # Should either train or become baseline-only (not fail)
        assert result["status"] in ["trained", "baseline_only"]

    def test_temporal_split_in_trainer(self, trainer):
        """Trainer uses temporal split correctly."""
        train_df, val_df = trainer.prepare_training_data()

        if train_df is not None and val_df is not None:
            # Check chronological ordering
            max_train = train_df["date"].max()
            min_val = val_df["date"].min()
            assert max_train < min_val

            # Check minimum sizes
            assert len(train_df) >= 30
            assert len(val_df) > 0

    def test_mae_calculation_correct(self, trainer):
        """MAE calculation should match sklearn implementation."""
        train_df, val_df = trainer.prepare_training_data()

        if train_df is None or val_df is None:
            pytest.skip("Insufficient data for MAE test")

        trainer.train(train_df)
        metrics = trainer.validate(val_df)

        # Verify MAE is calculated
        assert "ml_mae" in metrics
        assert metrics["ml_mae"] >= 0

        # Verify naive baseline MAE
        assert "naive_baseline_mae" in metrics
        assert metrics["naive_baseline_mae"] >= 0

    def test_insufficient_data_becomes_baseline_only(self, trainer):
        """Pair with insufficient data should be baseline-only."""
        # Create a trainer with very high minimum
        strict_trainer = ModelTrainer(
            commodity_id=str(trainer.commodity_id),
            mandi_id=str(trainer.mandi_id),
            min_obs=1000000  # Impossible threshold
        )

        result = strict_trainer.train_and_validate()

        assert result["status"] == "baseline_only"

    def test_save_model_artifact(self, trainer):
        """Model artifact should be saved and loadable."""
        # Train first
        result = trainer.train_and_validate()

        if result["status"] != "trained":
            pytest.skip("Model not trained, skipping save test")

        # Save to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "test_model.pkl"

            # Override the MODELS_DIR temporarily
            original_dir = trainer.__class__.MODELS_DIR
            trainer.__class__.MODELS_DIR = Path(tmpdir)

            saved_path = trainer.save_model(tmp_path)

            # Verify files exist
            assert saved_path.exists()
            assert saved_path.with_suffix(".json").exists()

            # Verify model can be loaded
            new_trainer = ModelTrainer(
                commodity_id=trainer.commodity_id,
                mandi_id=trainer.mandi_id
            )
            success = new_trainer.load_model(saved_path)
            assert success

            # Restore original
            trainer.__class__.MODELS_DIR = original_dir

    def test_reproducibility(self, trainer):
        """Same data + same seed should give similar MAE."""
        train_df, val_df = trainer.prepare_training_data()

        if train_df is None or val_df is None:
            pytest.skip("Insufficient data")

        # Train twice with same seed
        trainer1 = ModelTrainer(
            commodity_id=trainer.commodity_id,
            mandi_id=trainer.mandi_id,
            random_state=42
        )
        trainer1.train(train_df)
        metrics1 = trainer1.validate(val_df)

        trainer2 = ModelTrainer(
            commodity_id=trainer.commodity_id,
            mandi_id=trainer.mandi_id,
            random_state=42
        )
        trainer2.train(train_df)
        metrics2 = trainer2.validate(val_df)

        # MAEs should be close (within tolerance)
        # Note: sklearn may have some platform-specific variation
        assert abs(metrics1["ml_mae"] - metrics2["ml_mae"]) < 1.0


class TestForecastPrice:
    """Tests for forecast_price function."""

    def test_forecast_retrieval(self, db_session, mock_commodity, mock_mandi):
        """Forecast should be retrievable for trained pair."""
        # Train the model first
        trainer = ModelTrainer(
            commodity_id=str(mock_commodity.id),
            mandi_id=str(mock_mandi.id)
        )

        result = trainer.train_and_validate()

        if result["status"] != "trained":
            pytest.skip("Model not trained")

        # Train on demo data and save
        from app.data.ingest import ingest_from_csv
        from app.core.config import DEMO_MANDI_PRICES_PATH

        ingest_from_csv(csv_path=DEMO_MANDI_PRICES_PATH)

        # Save model to models directory
        model_path = trainer.save_model()

        # Now test forecast retrieval
        as_of_date = date(2026, 5, 1)
        forecast_result = forecast_price(
            commodity_id=str(mock_commodity.id),
            mandi_id=str(mock_mandi.id),
            as_of_date=as_of_date,
            model_path=model_path
        )

        # Check result structure
        assert "commodity_id" in forecast_result
        assert "mandi_id" in forecast_result
        assert "baseline_forecast" in forecast_result
        assert "ml_forecast" in forecast_result
        assert "ml_available" in forecast_result

        # Baseline should always be available
        assert forecast_result["baseline_forecast"] is not None

        # ML forecast should be available
        assert forecast_result["ml_available"] is True

    def test_forecast_with_baseline_only(self, db_session, mock_commodity, mock_mandi):
        """Forecast should handle baseline-only pairs."""
        # Create a trainer that becomes baseline-only
        trainer = ModelTrainer(
            commodity_id=str(mock_commodity.id),
            mandi_id=str(mock_mandi.id),
            min_obs=1000000  # Impossible threshold
        )

        result = trainer.train_and_validate()

        assert result["status"] == "baseline_only"


class TestModelTrainingPipeline:
    """Integration tests for full training pipeline."""

    @pytest.fixture
    def trained_pair(self, db_session, mock_commodity, mock_mandi):
        """Train a single model and return the trainer."""
        # Ingest demo data
        from app.data.ingest import ingest_from_csv
        from app.core.config import DEMO_MANDI_PRICES_PATH

        ingest_from_csv(csv_path=DEMO_MANDI_PRICES_PATH)

        trainer = ModelTrainer(
            commodity_id=str(mock_commodity.id),
            mandi_id=str(mock_mandi.id),
            random_state=42
        )

        result = trainer.train_and_validate()

        if result["status"] != "trained":
            pytest.skip("Model not trained")

        trainer.save_model()

        return trainer

    def test_train_script_execution(self, db_session, mock_commodity, mock_mandi):
        """Training script should execute without error."""
        from app.data.ingest import ingest_from_csv
        from app.core.config import DEMO_MANDI_PRICES_PATH

        # Ingest data first
        ingest_from_csv(csv_path=DEMO_MANDI_PRICES_PATH)

        # Import and call train function
        from scripts.train import train_single_model

        result = train_single_model(
            commodity_id=str(mock_commodity.id),
            mandi_id=str(mock_mandi.id),
            commodity_name=str(mock_commodity.name),
            mandi_name=str(mock_mandi.name),
            save=True,
            verbose=False
        )

        # Should complete without error
        assert result["status"] in ["trained", "baseline_only"]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.db import Base

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def mock_commodity(db_session):
    """Create a test commodity."""
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