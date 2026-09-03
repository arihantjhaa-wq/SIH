"""
Load Demo Fixtures Script for AgriDirect Pricing Engine MVP.
Loads mandi_prices.csv and weather.csv into PostgreSQL and verifies coverage.
"""
import sys
from datetime import datetime, date
from pathlib import Path
import pandas as pd

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import DEMO_MANDI_PRICES_PATH, DEMO_WEATHER_PATH
from app.core.db import get_db, Mandi, Commodity, MandiPrice, WeatherObservation
from app.data.ingest import ingest_from_csv
from scripts.seed_config import main as seed_configs_main


def load_weather_fixture():
    """Load data/demo/weather.csv into weather_observation table."""
    if not DEMO_WEATHER_PATH.exists():
        raise FileNotFoundError(f"Weather fixture not found at: {DEMO_WEATHER_PATH}")

    df = pd.read_csv(DEMO_WEATHER_PATH)
    inserted = 0
    updated = 0

    with get_db() as db:
        mandis = db.query(Mandi).all()
        mandi_map = {}
        for m in mandis:
            mandi_map[m.name.lower()] = m.id
            if m.agmarknet_code:
                mandi_map[m.agmarknet_code.lower()] = m.id

        for _, row in df.iterrows():
            m_key = str(row.get("agmarknet_code", "")).lower() or str(row.get("market", "")).lower()
            mandi_id = mandi_map.get(m_key)
            if not mandi_id:
                continue

            raw_date = row.get("obs_date")
            try:
                obs_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
            except ValueError:
                obs_date = datetime.strptime(str(raw_date), "%d/%m/%Y").date()

            rainfall = float(row.get("rainfall_mm", 0.0))
            temp_max = float(row.get("temp_max_c", 30.0))
            source = str(row.get("data_source", "demo_fixture"))

            existing = db.query(WeatherObservation).filter(
                WeatherObservation.mandi_id == mandi_id,
                WeatherObservation.obs_date == obs_date
            ).first()

            if existing:
                existing.rainfall_mm = rainfall
                existing.temp_max_c = temp_max
                existing.source = source
                updated += 1
            else:
                db.add(WeatherObservation(
                    mandi_id=mandi_id,
                    obs_date=obs_date,
                    rainfall_mm=rainfall,
                    temp_max_c=temp_max,
                    source=source
                ))
                inserted += 1

    print(f"Weather fixture: {inserted} inserted, {updated} updated.")


def verify_database_coverage():
    """Verify that every seeded crop and mandi has price and weather observations."""
    with get_db() as db:
        commodities = db.query(Commodity).all()
        mandis = db.query(Mandi).all()

        print("\n--- DATABASE COVERAGE VERIFICATION ---")
        print(f"Total Seeded Commodities: {len(commodities)}")
        print(f"Total Seeded Mandis: {len(mandis)}")

        total_prices = db.query(MandiPrice).count()
        total_weather = db.query(WeatherObservation).count()
        flagged_prices = db.query(MandiPrice).filter(MandiPrice.is_flagged_outlier == True).count()
        derived_modals = db.query(MandiPrice).filter(MandiPrice.is_derived_modal == True).count()

        print(f"Total Mandi Price Records: {total_prices}")
        print(f"Total Weather Records: {total_weather}")
        print(f"Flagged Outlier Records (Retained): {flagged_prices}")
        print(f"Derived Modal Price Records: {derived_modals}")

        print("\nPer-(Crop, Mandi) Pair Counts:")
        all_passed = True
        for c in commodities:
            for m in mandis:
                count = db.query(MandiPrice).filter(
                    MandiPrice.commodity_id == c.id,
                    MandiPrice.mandi_id == m.id
                ).count()
                if count < 60:
                    print(f"  [WARN] {c.name} @ {m.name}: {count} rows (<60 required)")
                    all_passed = False
                else:
                    print(f"  [OK]   {c.name:<10} @ {m.name:<12} ({m.agmarknet_code}): {count} observations")

        if all_passed:
            print("\n[SUCCESS] All crop/mandi combinations meet or exceed required observations!")
        else:
            print("\n[WARNING] Some combinations have insufficient observations.")


def main():
    print("Step 1: Ensuring configuration crops and mandis are seeded...")
    seed_configs_main()

    print("\nStep 2: Loading mandi prices demo fixture...")
    price_res = ingest_from_csv(DEMO_MANDI_PRICES_PATH, source_tag="demo_fixture")
    print(f"Mandi prices loaded: {price_res}")

    print("\nStep 3: Loading weather demo fixture...")
    load_weather_fixture()

    print("\nStep 4: Verifying database coverage...")
    verify_database_coverage()


if __name__ == "__main__":
    main()
