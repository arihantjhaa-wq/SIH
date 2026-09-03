"""
Config Seeding Script for AgriDirect Pricing Engine MVP.
Populates core.commodity and core.mandi from configs/crops.yaml and configs/mandis.yaml.
"""
import sys
import uuid
import yaml
from pathlib import Path

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import CROPS_CONFIG_PATH, MANDIS_CONFIG_PATH
from app.core.db import get_db, Commodity, Mandi


def seed_crops():
    """Seed crops from crops.yaml into commodity table."""
    if not CROPS_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Crops config not found at: {CROPS_CONFIG_PATH}")

    with open(CROPS_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    crops_data = config.get("crops", [])
    seeded_count = 0

    with get_db() as db:
        for item in crops_data:
            name = item["name"]
            # Deterministic UUID based on commodity name
            cid = uuid.uuid5(uuid.NAMESPACE_DNS, f"commodity.{name.lower()}")

            existing = db.query(Commodity).filter(Commodity.name == name).first()
            if existing:
                existing.category = item["category"]
                existing.unit = item.get("unit", "kg")
                existing.shelf_life_days = item.get("shelf_life_days")
                existing.is_active = item.get("is_active", True)
            else:
                commodity = Commodity(
                    id=cid,
                    name=name,
                    category=item["category"],
                    unit=item.get("unit", "kg"),
                    shelf_life_days=item.get("shelf_life_days"),
                    is_active=item.get("is_active", True)
                )
                db.add(commodity)
                seeded_count += 1

    print(f"Seeded/Updated {len(crops_data)} crops in database (newly added: {seeded_count}).")


def seed_mandis():
    """Seed mandis from mandis.yaml into mandi table."""
    if not MANDIS_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Mandis config not found at: {MANDIS_CONFIG_PATH}")

    with open(MANDIS_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    mandis_data = config.get("mandis", [])
    seeded_count = 0

    with get_db() as db:
        for item in mandis_data:
            name = item["name"]
            code = item.get("agmarknet_code", f"MH_{name.upper()}")
            # Deterministic UUID based on mandi code
            mid = uuid.uuid5(uuid.NAMESPACE_DNS, f"mandi.{code.lower()}")

            existing = db.query(Mandi).filter(
                (Mandi.agmarknet_code == code) | (Mandi.name == name)
            ).first()

            if existing:
                existing.name = name
                existing.state = item["state"]
                existing.district = item.get("district")
                existing.latitude = item["latitude"]
                existing.longitude = item["longitude"]
                existing.agmarknet_code = code
            else:
                mandi = Mandi(
                    id=mid,
                    name=name,
                    state=item["state"],
                    district=item.get("district"),
                    latitude=item["latitude"],
                    longitude=item["longitude"],
                    agmarknet_code=code
                )
                db.add(mandi)
                seeded_count += 1

    print(f"Seeded/Updated {len(mandis_data)} mandis in database (newly added: {seeded_count}).")


def main():
    print("Starting configuration seeding...")
    seed_crops()
    seed_mandis()
    print("Configuration seeding completed successfully.")


if __name__ == "__main__":
    main()
