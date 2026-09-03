"""
Database Migration Script for AgriDirect Pricing Engine MVP.
Creates or resets all tables defined in app.core.db.
"""
import sys
import argparse
from pathlib import Path

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import Base, engine


def run_migrations(reset: bool = False):
    """Create or reset database schema."""
    if reset:
        print("Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("Tables dropped successfully.")

    print("Creating tables defined in SQLAlchemy schema...")
    Base.metadata.create_all(bind=engine)
    print("Schema migration completed successfully!")
    print(f"Tables created/verified: {list(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AgriDirect DB Migrations")
    parser.add_argument("--reset", action="store_true", help="Drop all tables before creating")
    args = parser.parse_args()

    run_migrations(reset=args.reset)
