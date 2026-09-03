"""
Agmarknet Ingestion Client & Fallback Engine for AgriDirect Pricing Engine.
Fetches daily prices from data.gov.in Agmarknet resource, with automatic fallback
to data/demo/mandi_prices.csv when DEMO_MODE=true or API key is absent/fails.
"""
import logging
import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from pathlib import Path
import requests
import pandas as pd

from app.core.config import (
    AGMARKNET_API_KEY,
    AGMARKNET_BASE_URL,
    DEMO_MODE,
    DEMO_MANDI_PRICES_PATH,
)
from app.core.db import get_db, Mandi, Commodity, MandiPrice
from app.data.quality import clean_and_validate_record, clean_price_dataframe, to_kg

logger = logging.getLogger(__name__)


class AgmarknetClient:
    """
    HTTP Client for data.gov.in Agmarknet resource using the verified field mapping:
    state, district, market, commodity, variety, grade, arrival_date, min_price, max_price, modal_price.
    """

    def __init__(self, api_key: str = AGMARKNET_API_KEY, base_url: str = AGMARKNET_BASE_URL):
        self.api_key = api_key
        self.base_url = base_url

    def fetch_records(
        self,
        state: str = "Maharashtra",
        commodity: Optional[str] = None,
        limit: int = 500,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Fetch records from data.gov.in with retry/backoff on 5xx or network errors.
        """
        if not self.api_key:
            raise ValueError("AGMARKNET_API_KEY is not set.")

        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
            "filters[state]": state,
        }
        if commodity:
            params["filters[commodity]"] = commodity

        backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(self.base_url, params=params, timeout=(10.0, 20.0))
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("records", [])
                    return records
                elif response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    time.sleep(retry_after)
                elif response.status_code >= 500:
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    response.raise_for_status()
            except requests.RequestException as e:
                if attempt == max_retries:
                    raise RuntimeError(f"Failed to fetch Agmarknet data after {max_retries} attempts: {e}") from e
                time.sleep(backoff)
                backoff *= 2.0

        return []


def ingest_from_csv(
    csv_path: Path = DEMO_MANDI_PRICES_PATH,
    source_tag: str = "demo_fixture"
) -> Dict[str, Any]:
    """
    Load mandi prices from a CSV file (demo fixture), apply quality pipeline,
    and persist into PostgreSQL mandi_price table.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Fixture CSV not found at: {csv_path}")

    df = pd.read_csv(csv_path)
    cleaned_df = clean_price_dataframe(df)

    inserted_count = 0
    updated_count = 0
    flagged_count = 0

    with get_db() as db:
        # Build lookup maps for mandis and commodities
        mandis = db.query(Mandi).all()
        mandi_map = {}
        for m in mandis:
            mandi_map[m.name.lower()] = m.id
            if m.agmarknet_code:
                mandi_map[m.agmarknet_code.lower()] = m.id

        commodities = db.query(Commodity).all()
        commodity_map = {c.name.lower(): c.id for c in commodities}

        for _, row in cleaned_df.iterrows():
            m_key = str(row.get("agmarknet_code", "")).lower() or str(row.get("market", "")).lower()
            c_key = str(row.get("commodity", "")).lower()

            mandi_id = mandi_map.get(m_key) or mandi_map.get(str(row.get("market", "")).lower())
            commodity_id = commodity_map.get(c_key)

            if not mandi_id or not commodity_id:
                # Skip if mandi or commodity is unseeded
                continue

            raw_date = row.get("arrival_date") or row.get("price_date")
            if isinstance(raw_date, str):
                try:
                    price_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
                except ValueError:
                    price_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
            elif isinstance(raw_date, (pd.Timestamp, datetime)):
                price_date = raw_date.date()
            elif isinstance(raw_date, date):
                price_date = raw_date
            else:
                continue

            is_outlier = bool(row.get("is_flagged_outlier", False))
            is_derived = bool(row.get("is_derived_modal", False))
            if is_outlier:
                flagged_count += 1

            modal_val = row.get("modal_price")
            if pd.isna(modal_val):
                continue

            # Convert from AGMARKNET ₹/quintal to internal ₹/kg
            modal_val = to_kg(float(modal_val))

            min_val = to_kg(float(row.get("min_price"))) if pd.notna(row.get("min_price")) else None
            max_val = to_kg(float(row.get("max_price"))) if pd.notna(row.get("max_price")) else None
            arrival_qty = row.get("arrival_qty") if pd.notna(row.get("arrival_qty")) else None

            existing = db.query(MandiPrice).filter(
                MandiPrice.mandi_id == mandi_id,
                MandiPrice.commodity_id == commodity_id,
                MandiPrice.price_date == price_date
            ).first()

            if existing:
                existing.min_price = min_val
                existing.max_price = max_val
                existing.modal_price = modal_val
                existing.arrival_qty = arrival_qty
                existing.is_flagged_outlier = is_outlier
                existing.is_derived_modal = is_derived
                existing.source = source_tag
                updated_count += 1
            else:
                record = MandiPrice(
                    mandi_id=mandi_id,
                    commodity_id=commodity_id,
                    price_date=price_date,
                    min_price=min_val,
                    max_price=max_val,
                    modal_price=modal_val,
                    arrival_qty=arrival_qty,
                    is_flagged_outlier=is_outlier,
                    is_derived_modal=is_derived,
                    source=source_tag
                )
                db.add(record)
                inserted_count += 1

    return {
        "status": "success",
        "source": source_tag,
        "total_rows_processed": len(cleaned_df),
        "inserted": inserted_count,
        "updated": updated_count,
        "flagged_outliers": flagged_count
    }


def ingest_market_prices(
    state: str = "Maharashtra",
    commodity: Optional[str] = None,
    force_demo: bool = False
) -> Dict[str, Any]:
    """
    Primary ingestion entry point with automatic fallback:
    1. If DEMO_MODE=true or force_demo=true or AGMARKNET_API_KEY is empty: loads demo fixture.
    2. Otherwise attempts live Agmarknet API call.
    3. If live call fails: logs error and falls back to demo fixture.
    """
    should_use_demo = DEMO_MODE or force_demo or not AGMARKNET_API_KEY

    if should_use_demo:
        logger.info("Ingesting mandi prices via fallback DEMO_FIXTURE path...")
        return ingest_from_csv(csv_path=DEMO_MANDI_PRICES_PATH, source_tag="demo_fixture")

    # Attempt live ingestion
    client = AgmarknetClient(api_key=AGMARKNET_API_KEY)
    try:
        logger.info(f"Attempting live Agmarknet ingestion for state={state}, commodity={commodity}...")
        records = client.fetch_records(state=state, commodity=commodity)
        if not records:
            logger.warning("No records returned from live API; falling back to demo fixture.")
            return ingest_from_csv(csv_path=DEMO_MANDI_PRICES_PATH, source_tag="demo_fixture")

        df = pd.DataFrame(records)
        cleaned_df = clean_price_dataframe(df)

        # Ingest live records
        with get_db() as db:
            mandis = {m.name.lower(): m.id for m in db.query(Mandi).all()}
            commodities = {c.name.lower(): c.id for c in db.query(Commodity).all()}

            inserted, updated, flagged = 0, 0, 0
            for _, row in cleaned_df.iterrows():
                m_name = str(row.get("market", "")).lower()
                c_name = str(row.get("commodity", "")).lower()
                mandi_id = mandis.get(m_name)
                commodity_id = commodities.get(c_name)

                if not mandi_id or not commodity_id:
                    continue

                raw_date = row.get("arrival_date")
                try:
                    price_date = datetime.strptime(str(raw_date), "%d/%m/%Y").date()
                except ValueError:
                    price_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()

                modal_val = to_kg(float(row.get("modal_price", 0)))
                min_val = to_kg(float(row.get("min_price"))) if pd.notna(row.get("min_price")) else None
                max_val = to_kg(float(row.get("max_price"))) if pd.notna(row.get("max_price")) else None
                is_outlier = bool(row.get("is_flagged_outlier", False))
                is_derived = bool(row.get("is_derived_modal", False))

                existing = db.query(MandiPrice).filter(
                    MandiPrice.mandi_id == mandi_id,
                    MandiPrice.commodity_id == commodity_id,
                    MandiPrice.price_date == price_date
                ).first()

                if existing:
                    existing.min_price = min_val
                    existing.max_price = max_val
                    existing.modal_price = modal_val
                    existing.is_flagged_outlier = is_outlier
                    existing.is_derived_modal = is_derived
                    existing.source = "live"
                    updated += 1
                else:
                    db.add(MandiPrice(
                        mandi_id=mandi_id,
                        commodity_id=commodity_id,
                        price_date=price_date,
                        min_price=min_val,
                        max_price=max_val,
                        modal_price=modal_val,
                        is_flagged_outlier=is_outlier,
                        is_derived_modal=is_derived,
                        source="live"
                    ))
                    inserted += 1

                if is_outlier:
                    flagged += 1

        return {
            "status": "success",
            "source": "live",
            "total_rows_processed": len(cleaned_df),
            "inserted": inserted,
            "updated": updated,
            "flagged_outliers": flagged
        }
    except Exception as e:
        logger.error(f"Live Agmarknet ingestion failed ({e}); falling back to demo fixture.")
        return ingest_from_csv(csv_path=DEMO_MANDI_PRICES_PATH, source_tag="demo_fixture")
