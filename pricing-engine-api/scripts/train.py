#!/usr/bin/env python
"""
Training script for AgriDirect Pricing Engine ML models.

Trains HistGradientBoostingRegressor models per (crop, mandi) pair
or pooled model fallback, with temporal walk-forward validation.
"""
import argparse
import json
import logging
import pickle
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from app.core.db import get_db_session, Commodity, Mandi, MandiPrice
from app.forecasting.sklearn_model import (
    ModelTrainer,
    TemporalSplitter,
    MIN_OBSERVATIONS_FOR_TRAINING,
    VALIDATION_SPLIT_RATIO,
    RANDOM_STATE,
    MODELS_DIR
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_crop_mandi_pairs(limit: Optional[int] = None) -> List[tuple]:
    """
    Get all (commodity, mandi) pairs with data.

    Returns:
        List of (commodity_id, mandi_id, commodity_name, mandi_name) tuples
    """
    with get_db_session() as session:
        commodities = session.query(Commodity).all()
        mandis = session.query(Mandi).all()

        pairs = []
        for commodity in commodities:
            for mandi in mandis:
                # Check if this pair has any data
                count = session.query(MandiPrice).filter(
                    MandiPrice.commodity_id == commodity.id,
                    MandiPrice.mandi_id == mandi.id
                ).count()

                pairs.append((commodity.id, mandi.id, commodity.name, mandi.name, count))

        # Sort by count descending
        pairs.sort(key=lambda x: x[4], reverse=True)

        if limit:
            pairs = pairs[:limit]

        return pairs


def train_single_model(
    commodity_id: str,
    mandi_id: str,
    commodity_name: str,
    mandi_name: str,
    save: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Train a single per-(crop, mandi) model.

    Args:
        commodity_id: UUID of commodity
        mandi_id: UUID of mandi
        commodity_name: Name for logging
        mandi_name: Name for logging
        save: Whether to save model artifacts
        verbose: Whether to log progress

    Returns:
        Dictionary with training results
    """
    if verbose:
        logger.info(f"Training model for {commodity_name} @ {mandi_name}...")

    trainer = ModelTrainer(
        commodity_id=str(commodity_id),
        mandi_id=str(mandi_id),
        random_state=RANDOM_STATE,
        min_obs=MIN_OBSERVATIONS_FOR_TRAINING
    )

    result = trainer.train_and_validate()

    if verbose:
        if result["status"] == "baseline_only":
            logger.warning(f"  → Baseline-only: {result.get('reason')}")
        else:
            logger.info(f"  → Training MAE: {result.get('training_mae', 'N/A'):.2f}")
            logger.info(f"  → Validation MAE (ML): {result.get('ml_mae', 'N/A'):.2f}")
            logger.info(f"  → Validation MAE (naive lag-1): {result.get('naive_baseline_mae', 'N/A'):.2f}")

            if result.get("ml_mae") and result.get("naive_baseline_mae"):
                if result["ml_mae"] < result["naive_baseline_mae"]:
                    logger.info(f"  → ✓ ML beats naive baseline by {result['naive_baseline_mae'] - result['ml_mae']:.2f}")
                else:
                    logger.warning(f"  → ⚠ ML underperforms naive baseline")

    # Save model if trained
    if save and result["status"] == "trained":
        model_path = trainer.save_model()
        if verbose:
            logger.info(f"  → Model saved to: {model_path}")
        result["model_path"] = str(model_path)

    return result


def train_all_models(
    limit_pairs: Optional[int] = None,
    save: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Train models for all (crop, mandi) pairs.

    Args:
        limit_pairs: Maximum number of pairs to train (for testing)
        save: Whether to save model artifacts
        verbose: Whether to log progress

    Returns:
        Dictionary with aggregate results
    """
    logger.info("=" * 60)
    logger.info("AgriDirect Pricing Engine - ML Training")
    logger.info("=" * 60)

    pairs = get_crop_mandi_pairs(limit=limit_pairs)

    if verbose:
        logger.info(f"Found {len(pairs)} (crop, mandi) pairs")
        logger.info(f"Minimum observations for training: {MIN_OBSERVATIONS_FOR_TRAINING}")
        logger.info(f"Validation split: {VALIDATION_SPLIT_RATIO:.0%} (temporal, never shuffled)")
        logger.info(f"Models directory: {MODELS_DIR}")
        logger.info("")

    results = {
        "training_timestamp": datetime.now().isoformat(),
        "total_pairs": len(pairs),
        "trained": [],
        "baseline_only": [],
        "failed": [],
        "aggregate_metrics": {}
    }

    # Track aggregate metrics
    trained_ml_maes = []
    trained_naive_maes = []
    trained_counts = []

    for commodity_id, mandi_id, commodity_name, mandi_name, obs_count in pairs:
        # Skip if too few observations (already filtered, but double-check)
        if obs_count < MIN_OBSERVATIONS_FOR_TRAINING:
            if verbose:
                logger.info(f"Skipping {commodity_name} @ {mandi_name}: only {obs_count} observations")
            results["baseline_only"].append({
                "commodity": commodity_name,
                "mandi": mandi_name,
                "reason": f"Only {obs_count} observations (needs ≥{MIN_OBSERVATIONS_FOR_TRAINING})"
            })
            continue

        result = train_single_model(
            commodity_id, mandi_id, commodity_name, mandi_name,
            save=save, verbose=verbose
        )

        # Categorize result
        if result["status"] == "trained":
            results["trained"].append(result)
            trained_ml_maes.append(result["ml_mae"])
            trained_naive_maes.append(result["naive_baseline_mae"])
            trained_counts.append((commodity_name, mandi_name, result["n_training"], result["n_validation"]))
        elif result["status"] == "baseline_only":
            results["baseline_only"].append(result)
        else:
            results["failed"].append(result)

    # Calculate aggregate metrics
    if trained_ml_maes:
        results["aggregate_metrics"] = {
            "avg_ml_mae": float(np.mean(trained_ml_maes)),
            "avg_naive_mae": float(np.mean(trained_naive_maes)),
            "std_ml_mae": float(np.std(trained_ml_maes)),
            "min_ml_mae": float(np.min(trained_ml_maes)),
            "max_ml_mae": float(np.max(trained_ml_maes)),
            "ml_beats_naive_count": sum(m < n for m, n in zip(trained_ml_maes, trained_naive_maes)),
            "total_trained": len(trained_ml_maes)
        }

    # Log summary
    if verbose:
        logger.info("")
        logger.info("=" * 60)
        logger.info("Training Summary")
        logger.info("=" * 60)
        logger.info(f"  Total pairs:           {results['total_pairs']}")
        logger.info(f"  Trained (ML available): {len(results['trained'])}")
        logger.info(f"  Baseline-only:         {len(results['baseline_only'])}")
        logger.info(f"  Failed:                {len(results['failed'])}")

        if results["aggregate_metrics"]:
            logger.info("")
            logger.info(f"  Average ML MAE:           {results['aggregate_metrics']['avg_ml_mae']:.2f}")
            logger.info(f"  Average naive MAE:        {results['aggregate_metrics']['avg_naive_mae']:.2f}")
            logger.info(f"  ML beats naive:           {results['aggregate_metrics']['ml_beats_naive_count']}/{results['aggregate_metrics']['total_trained']}")

        # Show per-pair breakdown
        if trained_counts:
            logger.info("")
            logger.info("  Per-pair details:")
            for commodity, mandi, n_train, n_val in trained_counts:
                logger.info(f"    {commodity} @ {mandi}: n_train={n_train}, n_val={n_val}")

    # Save training report
    if save:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = MODELS_DIR / "training_report.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        if verbose:
            logger.info(f"\n  Training report saved to: {report_path}")

    return results


def train_pooled_model(verbose: bool = True) -> Dict[str, Any]:
    """
    Train a single pooled model with all crops/mandis as features.

    This is the acceptable fallback if per-pair training is infeasible.
    """
    if verbose:
        logger.info("Training pooled model (all crops/mandis)...")
        logger.warning("Note: Pooled model is the acceptable MVP fallback")

    # For MVP: pooled model not yet implemented (per-pair is preferred)
    # This is the placeholder for the alternative approach

    logger.error("Pooled model not implemented - per-pair training is preferred")
    return {"error": "Pooled model not implemented"}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Train AgriDirect Pricing Engine ML models"
    )

    parser.add_argument(
        "--crop", type=str, default=None,
        help="Train only for specific crop (e.g., 'Tomato')"
    )

    parser.add_argument(
        "--mandi", type=str, default=None,
        help="Train only for specific mandi (e.g., 'Pune')"
    )

    parser.add_argument(
        "--all-crops", action="store_true",
        help="Train for all crops and mandis"
    )

    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit to N pairs (for testing)"
    )

    parser.add_argument(
        "--no-save", action="store_true",
        help="Do not save model artifacts"
    )

    parser.add_argument(
        "--verbose", action="store_true", default=True,
        help="Verbose logging (default: True)"
    )

    parser.add_argument(
        "--pool", action="store_true",
        help="Train pooled model (acceptable fallback)"
    )

    args = parser.parse_args()

    # Handle pooled mode
    if args.pool:
        train_pooled_model(verbose=args.verbose)
        return

    # Handle specific crop/mandi training
    if args.crop and args.mandi:
        with get_db_session() as session:
            commodity = session.query(Commodity).filter_by(name=args.crop).first()
            mandi = session.query(Mandi).filter_by(name=args.mandi).first()

            if not commodity:
                logger.error(f"Crop not found: {args.crop}")
                return
            if not mandi:
                logger.error(f"Mandi not found: {args.mandi}")
                return

            train_single_model(
                commodity.id, mandi.id, commodity.name, mandi.name,
                save=not args.no_save, verbose=args.verbose
            )

    # Train all crops
    elif args.all_crops or args.crop or args.mandi:
        results = train_all_models(
            limit_pairs=args.limit,
            save=not args.no_save,
            verbose=args.verbose
        )

        # Handle non-zero exit on failure
        if results["failed"]:
            raise SystemExit(f"Training failed for {len(results['failed'])} pairs")

    else:
        # Default: train all pairs
        results = train_all_models(
            limit_pairs=args.limit,
            save=not args.no_save,
            verbose=args.verbose
        )


if __name__ == "__main__":
    main()