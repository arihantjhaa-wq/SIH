"""
Dataset service — loads and queries the local agricultural prices JSON file.
"""

import json
from pathlib import Path
from typing import Optional
import pandas as pd


class DatasetService:
    """Manage local agricultural price dataset."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._data = None

    def _load(self):
        """Load JSON dataset once, cache in memory."""
        if self._data is None:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                print(f"[Dataset] Loaded {len(self._data.get('daily_prices', []))} records")
            except Exception as e:
                print(f"[Dataset] Error loading: {e}")
                self._data = {"daily_prices": []}
        return self._data

    def get_historical_prices(
        self,
        state: str,
        commodity: str
    ) -> Optional[pd.DataFrame]:
        """
        Query historical price records for a commodity in a state.

        Returns:
            DataFrame with columns: date, modal_price_inr
            or None if no records found
        """
        data = self._load()

        try:
            records = [
                {
                    "date": pd.to_datetime(row["date"]),
                    "modal_price_inr": float(row.get("modal_price_inr_per_kg", 0))
                }
                for row in data.get("daily_prices", [])
                if (row.get("state_name", "").lower() == state.lower() and
                    row.get("commodity_name", "").lower() == commodity.lower())
            ]

            if not records:
                print(
                    f"[Dataset] No records for {commodity} in {state}"
                )
                return None

            df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
            print(
                f"[Dataset] Found {len(df)} records for {commodity} in {state}"
            )
            return df

        except Exception as e:
            print(f"[Dataset] Error querying: {e}")
            return None


# Global instance
_dataset = None


def get_dataset_service(file_path: str) -> DatasetService:
    """Get or create dataset service singleton."""
    global _dataset
    if _dataset is None:
        _dataset = DatasetService(file_path)
    return _dataset
