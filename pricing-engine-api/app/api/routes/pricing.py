"""Pricing API routes — Stage 9.

This module implements the pricing estimate endpoint that exposes the
existing Stage 6-8 pricing pipeline through a clean HTTP interface.

The API is an adapter layer only — it does not duplicate any pricing,
logistics, or integration formulas.
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, HTTPException

from app.api.schemas.pricing import (
    ErrorResponse,
    PricingRequest,
    PricingResponse,
)
from app.pricing.integration import compute_end_to_end_price, PricingIntegrationError
from app.pricing.engine import predict_price
from app.logistics.engine import estimate_logistics
from app.logistics.validate import LogisticsValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_commodity_id(commodity: str) -> str:
    """Map commodity name to UUID — must match seed_config.py's deterministic UUID5."""
    import uuid

    lower = commodity.lower()
    # Verify it's a known crop, then derive the same UUID the DB seed uses.
    known = {
        "tomato", "onion", "potato", "rice", "wheat",
        "maize", "groundnut", "soybean", "mustard", "gram",
        "lentil", "pigeon pea", "cabbage", "cauliflower", "green chilli",
        "brinjal", "mango", "banana", "orange", "apple",
    }
    if lower not in known:
        return None
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"commodity.{lower}"))


def _get_mandi_id(farmer_lat: float, farmer_lon: float) -> str:
    """Map farmer location to nearest mandi UUID.

    For the MVP, we use a simple proximity-based mapping using
    the mandis configured in mandis.yaml.
    """
    import math
    from pathlib import Path
    import yaml

    config_path = Path(__file__).parent.parent.parent.parent / "configs" / "mandis.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            mandis_config = yaml.safe_load(f)
    except Exception:
        # Fallback to Pune mandi
        return "97ce83b2-322f-5c5c-8fce-22f2eacdd677"

    mandi_uuids = {
        "MH_PUNE": "97ce83b2-322f-5c5c-8fce-22f2eacdd677",
        "MH_NASHIK": "aa3c1513-a3bd-548d-9d87-9ed8d68be039",
        "MH_LASALGAON": "80b63707-7157-59be-8b1e-e3d3c6f44419",
        "MH_VASHI": "304c7c54-8863-5a0a-a07d-bebef5e0af1c",
        "MH_NAGPUR": "3ec75dd7-45a8-5521-98bc-d6b4c1412a2b",
        "MH_KOLHAPUR": "112fcfa1-8c94-52ae-91a6-abb7dc6ec8b5",
        "MH_AHMEDNAGAR": "aa3c1513-a3bd-548d-9d87-9ed8d68be039",
    }

    # Find nearest mandi by simple Euclidean distance (sufficient for India)
    min_dist = float("inf")
    nearest_mandi = "MH_PUNE"

    for mandi in mandis_config.get("mandis", []):
        code = mandi.get("agmarknet_code", "")
        m_lat = mandi.get("latitude", 0)
        m_lon = mandi.get("longitude", 0)

        # Simple distance (good enough for mandi selection)
        dist = math.sqrt((farmer_lat - m_lat) ** 2 + (farmer_lon - m_lon) ** 2)
        if dist < min_dist:
            min_dist = dist
            nearest_mandi = code

    return mandi_uuids.get(nearest_mandi, "97ce83b2-322f-5c5c-8fce-22f2eacdd677")


@router.post(
    "/estimate",
    response_model=PricingResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Calculate pricing estimate",
    description="Compute end-to-end pricing for a commodity shipment including farmer payout, logistics, platform fee, and final buyer price.",
)
async def estimate_pricing(request: PricingRequest) -> PricingResponse:
    """
    Calculate pricing estimate for a commodity shipment.

    This endpoint executes the full Stage 6-8 pricing pipeline:
    - Stage 6: Price discovery, fair price, reliability, farmer protection
    - Stage 7: Logistics calculation (distance, transport, handling)
    - Stage 8: End-to-end integration (buyer price, explanations)

    The API is an adapter layer only — it calls existing modules without
    duplicating any pricing or logistics formulas.
    """
    try:
        # Step 1: Map commodity name to UUID
        commodity_id = _get_commodity_id(request.commodity)
        if commodity_id is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_COMMODITY",
                        "message": f"Unknown commodity: '{request.commodity}'. Valid commodities: tomato, onion, potato, rice, wheat, maize, groundnut, soybean, mustard, gram, lentil, pigeon pea, cabbage, cauliflower, green chilli, brinjal, mango, banana, orange, apple",
                        "field": "commodity",
                    }
                },
            )

        # Step 2: Map farmer location to nearest mandi UUID
        mandi_id = _get_mandi_id(
            request.farmer_location.lat,
            request.farmer_location.lon,
        )

        # Step 3: Run Stage 6 pricing engine
        pricing_result = predict_price(
            commodity_id=commodity_id,
            mandi_id=mandi_id,
            as_of_date=date.today(),
            farmer_declared_minimum=request.farmer_declared_minimum,
            quantity_kg=request.quantity_kg,
        )

        # Check for insufficient data
        if pricing_result.get("status") == "INSUFFICIENT_DATA":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INSUFFICIENT_DATA",
                        "message": pricing_result.get("reason", "Insufficient data for pricing"),
                        "field": "pricing",
                    }
                },
            )

        # Step 4: Compute logistics (Stage 7)
        try:
            logistics_result = estimate_logistics(
                farmer_lat=request.farmer_location.lat,
                farmer_lon=request.farmer_location.lon,
                buyer_lat=request.buyer_location.lat,
                buyer_lon=request.buyer_location.lon,
                quantity_kg=request.quantity_kg,
            )
        except LogisticsValidationError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": e.code,
                        "message": e.message,
                        "field": e.field,
                    }
                },
            )

        # Step 5: Run Stage 8 end-to-end integration
        platform_fee_pct = request.platform_fee_pct if request.platform_fee_pct is not None else 0.05

        end_to_end_result = compute_end_to_end_price(
            pricing_result=pricing_result,
            logistics_result=logistics_result,
            platform_fee_pct=platform_fee_pct,
        )

        # Step 6: Convert to API response
        return PricingResponse(**end_to_end_result)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except PricingIntegrationError as e:
        # Convert pricing integration errors to HTTP 400
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "field": e.field,
                }
            },
        )

    except Exception as e:
        # Log unexpected errors and return generic 500
        logger.exception("Unexpected error in pricing estimate")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred while computing the pricing estimate",
                    "field": None,
                }
            },
        )
