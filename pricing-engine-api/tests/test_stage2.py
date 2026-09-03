"""
Stage 2 Test Suite for AgriDirect Pricing Engine MVP.
Verifies database migration, config seeding, data quality pipeline, fixture loading, and fallback path.
"""
# pyrefly: ignore [missing-import]
import pytest
import pandas as pd
from datetime import date

from app.core.config import DEMO_MODE, CROPS_CONFIG_PATH, MANDIS_CONFIG_PATH
from app.core.db import engine, Base, get_db, Commodity, Mandi, MandiPrice, WeatherObservation
from app.data.quality import (
    to_kg,
    to_quintal,
    clean_and_validate_record,
    clean_price_dataframe,
    filter_for_training
)
from app.data.ingest import ingest_market_prices, ingest_from_csv
from scripts.migrate import run_migrations
from scripts.seed_config import seed_crops, seed_mandis
from scripts.load_demo_fixture import load_weather_fixture


def test_schema_migration_fresh():
    """Verify that a fresh schema migration drops/creates all required tables without error."""
    run_migrations(reset=True)
    table_names = list(Base.metadata.tables.keys())
    expected_tables = ["commodity", "mandi", "mandi_price", "weather_observation", "demand_signal", "prediction_log"]
    for tbl in expected_tables:
        assert tbl in table_names, f"Expected table {tbl} was not created."


def test_config_seeding():
    """Verify that exactly the 20 crops and 7 mandis are seeded."""
    seed_crops()
    seed_mandis()

    with get_db() as db:
        commodities = db.query(Commodity).all()
        assert len(commodities) == 20
        crop_names = {c.name for c in commodities}
        expected_names = {"Tomato", "Onion", "Potato", "Rice", "Wheat",
                         "Maize", "Groundnut", "Soybean", "Mustard", "Gram",
                         "Lentil", "Pigeon Pea", "Cabbage", "Cauliflower", "Green Chilli",
                         "Brinjal", "Mango", "Banana", "Orange", "Apple"}
        assert crop_names == expected_names

        mandis = db.query(Mandi).all()
        assert len(mandis) == 7
        assert all(m.state == "Maharashtra" for m in mandis)
        assert all(m.latitude is not None and m.longitude is not None for m in mandis)


def test_unit_conversion():
    """Verify ₹/quintal to ₹/kg single-boundary conversion."""
    # 2200 ₹/quintal -> 22.0 ₹/kg
    assert to_kg(2200) == 22.0
    assert to_kg(0) == 0.0
    assert to_quintal(22.0) == 2200.0


def test_missing_modal_price_derivation():
    """Verify that missing modal price is derived as (min + max) / 2 and flagged."""
    raw_record = {
        "min_price": 1800.0,
        "max_price": 2200.0,
        "modal_price": None
    }
    cleaned, flags = clean_and_validate_record(raw_record)
    assert cleaned["modal_price"] == 2000.0
    assert flags["is_derived_modal"] is True
    assert flags["is_flagged_outlier"] is False


def test_inverted_min_max_swap_correction():
    """Verify that min_price > max_price is swap-corrected."""
    raw_record = {
        "min_price": 3000.0,
        "max_price": 2500.0,
        "modal_price": 2700.0
    }
    cleaned, flags = clean_and_validate_record(raw_record)
    assert cleaned["min_price"] == 2500.0
    assert cleaned["max_price"] == 3000.0
    assert flags["is_swap_corrected"] is True


def test_outlier_detection_and_training_exclusion():
    """Verify that invalid/extreme prices are flagged, retained, and excluded from training."""
    # Non-positive price
    rec_zero = {"min_price": 0.0, "max_price": 0.0, "modal_price": 0.0}
    cleaned_zero, flags_zero = clean_and_validate_record(rec_zero)
    assert flags_zero["is_flagged_outlier"] is True
    assert flags_zero["outlier_reason"] == "non_positive_price"

    # Extreme spike (>20x rolling median)
    rec_spike = {"min_price": 40000.0, "max_price": 50000.0, "modal_price": 45000.0}
    cleaned_spike, flags_spike = clean_and_validate_record(rec_spike, rolling_median_30d=2000.0)
    assert flags_spike["is_flagged_outlier"] is True
    assert flags_spike["outlier_reason"] == "extreme_spike_gt_20x_median"

    # Normal price (not an outlier)
    rec_normal = {"min_price": 1900.0, "max_price": 2300.0, "modal_price": 2100.0}
    cleaned_normal, flags_normal = clean_and_validate_record(rec_normal, rolling_median_30d=2000.0)
    assert flags_normal["is_flagged_outlier"] is False

    # DataFrame filtering check
    df = pd.DataFrame([cleaned_zero, cleaned_spike, cleaned_normal])
    train_df = filter_for_training(df)
    assert len(train_df) == 1
    assert train_df.iloc[0]["modal_price"] == 2100.0


def test_demo_fixture_loading_and_coverage():
    """Verify that the demo dataset loads and provides >= 60 observations for every crop/mandi pair."""
    # Ingest prices from demo CSV
    res = ingest_from_csv()
    assert res["status"] == "success"
    assert res["source"] == "demo_fixture"
    assert res["total_rows_processed"] >= 4000

    # Load weather
    load_weather_fixture()

    with get_db() as db:
        commodities = db.query(Commodity).all()
        mandis = db.query(Mandi).all()

        for c in commodities:
            for m in mandis:
                count = db.query(MandiPrice).filter(
                    MandiPrice.commodity_id == c.id,
                    MandiPrice.mandi_id == m.id
                ).count()
                assert count >= 60, f"Insufficient observations ({count}) for {c.name} @ {m.name}"

        # Weather observations exist for each mandi
        for m in mandis:
            w_count = db.query(WeatherObservation).filter(WeatherObservation.mandi_id == m.id).count()
            assert w_count >= 60, f"Insufficient weather observations for {m.name}"


def test_demo_mode_fallback_activation():
    """Verify that ingest_market_prices falls back to demo fixture and sets source='demo_fixture'."""
    result = ingest_market_prices(state="Maharashtra", force_demo=True)
    assert result["status"] == "success"
    assert result["source"] == "demo_fixture"
    assert result["total_rows_processed"] > 0

    with get_db() as db:
        sample = db.query(MandiPrice).first()
        assert sample is not None
        assert sample.source == "demo_fixture"
