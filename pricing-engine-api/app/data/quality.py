"""
Data Quality and Validation Pipeline for AgriDirect Pricing Engine.
Implements missing modal price derivation, outlier detection, and unit conversion.
"""
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
from decimal import Decimal


def to_kg(price_quintal: float | Decimal | int) -> float:
    """
    Convert price from ₹/quintal (Agmarknet canonical storage) to ₹/kg (internal engine unit).
    1 quintal = 100 kg.
    """
    if price_quintal is None:
        return 0.0
    return float(price_quintal) / 100.0


def to_quintal(price_kg: float | Decimal | int) -> float:
    """Convert price from ₹/kg to ₹/quintal."""
    if price_kg is None:
        return 0.0
    return float(price_kg) * 100.0


def clean_and_validate_record(
    record: Dict[str, Any],
    rolling_median_30d: Optional[float] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Validates and cleans a single mandi price record.
    Returns (cleaned_record, flags).

    Rules:
    1. min_price > max_price: swap correct.
    2. missing modal_price: derive as (min_price + max_price) / 2 and flag is_derived_modal=True.
    3. price <= 0: flag is_flagged_outlier=True (non_positive_price).
    4. price > 20 * 30-day median: flag is_flagged_outlier=True (extreme_spike).
    5. Flagged records are retained, never deleted.
    """
    cleaned = dict(record)
    flags = {
        "is_derived_modal": False,
        "is_swap_corrected": False,
        "is_flagged_outlier": False,
        "outlier_reason": None,
    }

    min_p = cleaned.get("min_price")
    max_p = cleaned.get("max_price")
    modal_p = cleaned.get("modal_price")

    # Cast to float if present
    min_val = float(min_p) if min_p is not None and not pd.isna(min_p) else None
    max_val = float(max_p) if max_p is not None and not pd.isna(max_p) else None
    modal_val = float(modal_p) if modal_p is not None and not pd.isna(modal_p) else None

    # Rule 1: Swap correction if min_price > max_price
    if min_val is not None and max_val is not None and min_val > max_val:
        min_val, max_val = max_val, min_val
        flags["is_swap_corrected"] = True

    # Rule 2: Derive missing modal price from min and max
    if (modal_val is None or pd.isna(modal_val)) and (min_val is not None and max_val is not None):
        modal_val = round((min_val + max_val) / 2.0, 2)
        flags["is_derived_modal"] = True

    # Rule 3: Check for non-positive prices
    if modal_val is not None and modal_val <= 0:
        flags["is_flagged_outlier"] = True
        flags["outlier_reason"] = "non_positive_price"
    elif min_val is not None and min_val < 0:
        flags["is_flagged_outlier"] = True
        flags["outlier_reason"] = "negative_min_price"
    elif max_val is not None and max_val < 0:
        flags["is_flagged_outlier"] = True
        flags["outlier_reason"] = "negative_max_price"

    # Rule 4: Outlier detection against 30-day rolling median
    if not flags["is_flagged_outlier"] and modal_val is not None and rolling_median_30d is not None:
        if rolling_median_30d > 0 and modal_val > (20.0 * rolling_median_30d):
            flags["is_flagged_outlier"] = True
            flags["outlier_reason"] = "extreme_spike_gt_20x_median"

    cleaned["min_price"] = min_val
    cleaned["max_price"] = max_val
    cleaned["modal_price"] = modal_val
    cleaned["is_derived_modal"] = flags["is_derived_modal"]
    cleaned["is_flagged_outlier"] = flags["is_flagged_outlier"]

    return cleaned, flags


def clean_price_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans a pandas DataFrame of price records, computing rolling 30-day medians
    per (commodity, market/mandi) pair to flag anomalies without dropping records.
    """
    if df.empty:
        return df

    out = df.copy()

    # Ensure price_date is datetime
    if "price_date" in out.columns:
        out["price_date"] = pd.to_datetime(out["price_date"])
    elif "arrival_date" in out.columns:
        out["price_date"] = pd.to_datetime(out["arrival_date"])

    # Ensure numeric columns
    for col in ["min_price", "max_price", "modal_price"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # Handle swap corrections
    swap_mask = (out["min_price"].notna()) & (out["max_price"].notna()) & (out["min_price"] > out["max_price"])
    if swap_mask.any():
        mins = out.loc[swap_mask, "min_price"].copy()
        maxs = out.loc[swap_mask, "max_price"].copy()
        out.loc[swap_mask, "min_price"] = maxs
        out.loc[swap_mask, "max_price"] = mins

    # Handle missing modal price derivation: (min + max) / 2
    missing_modal = out["modal_price"].isna() & out["min_price"].notna() & out["max_price"].notna()
    out["is_derived_modal"] = False
    if missing_modal.any():
        out.loc[missing_modal, "modal_price"] = ((out.loc[missing_modal, "min_price"] + out.loc[missing_modal, "max_price"]) / 2.0).round(2)
        out.loc[missing_modal, "is_derived_modal"] = True

    # Identify non-positive prices
    out["is_flagged_outlier"] = False
    non_pos_mask = (out["modal_price"] <= 0) | (out["min_price"] < 0) | (out["max_price"] < 0)
    out.loc[non_pos_mask, "is_flagged_outlier"] = True

    # Sort for rolling calculation
    group_cols = []
    if "commodity" in out.columns:
        group_cols.append("commodity")
    elif "commodity_id" in out.columns:
        group_cols.append("commodity_id")

    if "market" in out.columns:
        group_cols.append("market")
    elif "mandi_id" in out.columns:
        group_cols.append("mandi_id")
    elif "agmarknet_code" in out.columns:
        group_cols.append("agmarknet_code")

    if group_cols and "price_date" in out.columns:
        out = out.sort_values(group_cols + ["price_date"])
        # Compute 30-day rolling median of modal_price per group (shift by 1 to prevent leakage)
        def _rolling_med(s):
            return s.shift(1).rolling(window=30, min_periods=5).median()

        grouped = out.groupby(group_cols, group_keys=False)
        rolling_median = grouped["modal_price"].apply(_rolling_med)

        # Flag records where modal_price > 20 * rolling_median
        spike_mask = (rolling_median > 0) & (out["modal_price"] > (20.0 * rolling_median))
        out.loc[spike_mask, "is_flagged_outlier"] = True

    return out


def filter_for_training(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns only clean records suitable for model training.
    Excludes flagged outliers and records with missing modal prices.
    """
    if df.empty:
        return df
    clean = df[
        (~df["is_flagged_outlier"]) &
        (df["modal_price"].notna()) &
        (df["modal_price"] > 0)
    ].copy()
    return clean
