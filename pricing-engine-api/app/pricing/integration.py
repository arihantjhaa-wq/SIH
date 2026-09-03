"""
Stage 8 — End-to-End Pricing Integration.

Combines Stage 6 pricing output with Stage 7 logistics output into
one clean, deterministic, explainable result.

Pipeline preserved (no double-counting):

    Market Data → Baseline → ML Forecast → Fair Price
        → Farmer Protection → Reliability → Pricing Explanation
        → Logistics Calculation → Final Buyer Price → Final Explanation

Invariant:
    buyer_price_per_kg = farmer_payout_per_kg + logistics_cost_per_kg + platform_fee_per_kg
    buyer_total = farmer_total + logistics_total + platform_total
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

from app.logistics.engine import estimate_logistics
from app.logistics.cost import calculate_buyer_price


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_PLATFORM_FEE_PCT: float = 0.05  # 5%, Section 21


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class PricingIntegrationError(Exception):
    """Structured error for Stage 8 integration failures."""

    def __init__(self, field: str, message: str, code: str = "INTEGRATION_ERROR"):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> Dict[str, str]:
        return {"error": self.code, "field": self.field, "message": self.message}


def _validate_pricing_inputs(
    pricing_result: Dict[str, Any],
    platform_fee_pct: float,
) -> None:
    """Validate the pricing result before integration."""
    status = pricing_result.get("status")
    if status != "OK":
        raise PricingIntegrationError(
            field="pricing_result",
            message=f"Pricing result status is '{status}', expected 'OK'",
        )

    fair_price = pricing_result.get("fair_price")
    if fair_price is None or not isinstance(fair_price, (int, float)):
        raise PricingIntegrationError(
            field="fair_price",
            message=f"fair_price must be a number, got {fair_price!r}",
        )
    if math.isnan(fair_price) or math.isinf(fair_price):
        raise PricingIntegrationError(
            field="fair_price",
            message=f"fair_price must be finite, got {fair_price}",
        )

    baseline = pricing_result.get("baseline")
    if baseline is None or not isinstance(baseline, (int, float)):
        raise PricingIntegrationError(
            field="baseline",
            message=f"baseline must be a number, got {baseline!r}",
        )

    if not isinstance(platform_fee_pct, (int, float)) or platform_fee_pct < 0:
        raise PricingIntegrationError(
            field="platform_fee_pct",
            message=f"platform_fee_pct must be >= 0, got {platform_fee_pct!r}",
        )


def _validate_logistics_inputs(
    logistics_result: Dict[str, Any],
) -> None:
    """Validate the logistics result before integration."""
    for field in ("distance_km", "quantity_kg", "cost_per_kg", "total_logistics_cost"):
        val = logistics_result.get(field)
        if val is None or not isinstance(val, (int, float)):
            raise PricingIntegrationError(
                field=field,
                message=f"{field} must be a number, got {val!r}",
            )
        if math.isnan(val) or math.isinf(val):
            raise PricingIntegrationError(
                field=field,
                message=f"{field} must be finite, got {val}",
            )
        if val < 0:
            raise PricingIntegrationError(
                field=field,
                message=f"{field} must be >= 0, got {val}",
            )


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


def compute_end_to_end_price(
    pricing_result: Dict[str, Any],
    logistics_result: Optional[Dict[str, Any]] = None,
    platform_fee_pct: float = DEFAULT_PLATFORM_FEE_PCT,
    *,
    # Logistics passthrough — used when logistics_result is not pre-computed
    farmer_lat: Optional[float] = None,
    farmer_lon: Optional[float] = None,
    buyer_lat: Optional[float] = None,
    buyer_lon: Optional[float] = None,
    quantity_kg: Optional[float] = None,
    vehicle_capacity_kg: Optional[float] = None,
    cost_per_km: Optional[float] = None,
    handling_cost_per_point: float = 30.0,
    spoilage_buffer_per_kg: float = 0.0,
    use_road_factor: bool = True,
    road_factor: float = 1.3,
    fallback_distance_km: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute the complete end-to-end pricing result.

    Combines Stage 6 pricing (farmer payout, reliability, explanation)
    with Stage 7 logistics (distance, transport, handling) and applies
    platform fee to produce the final buyer price.

    Args:
        pricing_result: Output from predict_price() (Stage 6).
        logistics_result: Pre-computed output from estimate_logistics() (Stage 7),
            or None to compute logistics from the coordinates below.
        platform_fee_pct: Platform fee as fraction of farmer payout (default 5%).
        farmer_lat/lon, buyer_lat/lon: Coordinates for logistics (if not pre-computed).
        quantity_kg: Quantity for logistics (if not pre-computed).
        vehicle_capacity_kg, cost_per_km, handling_cost_per_point,
        spoilage_buffer_per_kg, use_road_factor, road_factor,
        fallback_distance_km: Logistics parameters.

    Returns:
        Complete end-to-end pricing result dict.
    """
    # ------------------------------------------------------------------
    # 1. Validate pricing result
    # ------------------------------------------------------------------
    _validate_pricing_inputs(pricing_result, platform_fee_pct)

    fair_price = float(pricing_result["fair_price"])
    baseline = float(pricing_result["baseline"])
    reliability = pricing_result.get("reliability")
    fair_price_range = pricing_result.get("fair_price_range", {})
    floor = pricing_result.get("floor")
    floor_blocked = pricing_result.get("floor_blocked", False)
    explanation = pricing_result.get("explanation", {})
    commodity_id = pricing_result.get("commodity_id")
    mandi_id = pricing_result.get("mandi_id")
    as_of_date = pricing_result.get("as_of_date")
    volatility_30d = pricing_result.get("volatility_30d")
    demand_index = pricing_result.get("demand_index")
    ml_forecast = pricing_result.get("ml_forecast")
    ml_available = pricing_result.get("ml_available", False)

    # ------------------------------------------------------------------
    # 2. Logistics — use pre-computed or compute now
    # ------------------------------------------------------------------
    if logistics_result is None:
        # Compute logistics from coordinates
        effective_qty = quantity_kg or 100.0
        logistics_result = estimate_logistics(
            farmer_lat=farmer_lat,
            farmer_lon=farmer_lon,
            buyer_lat=buyer_lat,
            buyer_lon=buyer_lon,
            quantity_kg=effective_qty,
            vehicle_capacity_kg=vehicle_capacity_kg,
            cost_per_km=cost_per_km,
            handling_cost_per_point=handling_cost_per_point,
            spoilage_buffer_per_kg=spoilage_buffer_per_kg,
            use_road_factor=use_road_factor,
            road_factor=road_factor,
            fallback_distance_km=fallback_distance_km,
        )

    _validate_logistics_inputs(logistics_result)

    logistics_per_kg = float(logistics_result["cost_per_kg"])
    logistics_total = float(logistics_result["total_logistics_cost"])
    quantity_kg_eff = float(logistics_result["quantity_kg"])
    distance_km = float(logistics_result["distance_km"])
    is_fallback = logistics_result.get("is_fallback", False)
    fallback_reason = logistics_result.get("fallback_reason")

    # ------------------------------------------------------------------
    # 3. Final buyer price
    # ------------------------------------------------------------------
    buyer = calculate_buyer_price(
        farmer_payout_per_kg=fair_price,
        logistics_cost_per_kg=logistics_per_kg,
        platform_fee_pct=platform_fee_pct,
    )
    platform_fee_per_kg = float(buyer["platform_fee_per_kg"])
    buyer_price_per_kg = float(buyer["buyer_price_per_kg"])

    # Totals — derive buyer_total from component totals to avoid
    # rounding divergence (e.g. round(a+b)*qty != round(a*qty)+round(b*qty)).
    farmer_total = round(fair_price * quantity_kg_eff, 2)
    logistics_total_calc = round(logistics_per_kg * quantity_kg_eff, 2)
    platform_total = round(platform_fee_per_kg * quantity_kg_eff, 2)
    buyer_total = round(farmer_total + logistics_total_calc + platform_total, 2)

    # ------------------------------------------------------------------
    # 4. Price consistency invariant (Section 8 / Stage 8 §5)
    #    buyer_price_per_kg = farmer_payout + logistics + platform_fee
    # ------------------------------------------------------------------
    recomputed = fair_price + logistics_per_kg + platform_fee_per_kg
    assert math.isclose(buyer_price_per_kg, recomputed, abs_tol=0.02), (
        f"Price consistency violated: {buyer_price_per_kg} != "
        f"{fair_price} + {logistics_per_kg} + {platform_fee_per_kg} = {recomputed}"
    )

    # buyer_total is derived as the sum of component totals — no second assert needed.

    # ------------------------------------------------------------------
    # 5. Farmer protection invariant (Section 8 / Stage 8 §6)
    # ------------------------------------------------------------------
    if floor is not None and not floor_blocked:
        assert fair_price >= float(floor) or fair_price >= float(floor) * 0.999, (
            f"Farmer protection violated: fair_price {fair_price} < floor {floor}"
        )

    # ------------------------------------------------------------------
    # 6. Price range — logistics must NOT alter Stage 6 range
    # ------------------------------------------------------------------
    range_low = fair_price_range.get("lower")
    range_high = fair_price_range.get("upper")

    # ------------------------------------------------------------------
    # 7. Build explanation payload
    # ------------------------------------------------------------------
    pricing_explanation = _build_pricing_explanation(
        baseline=baseline,
        ml_forecast=ml_forecast,
        ml_available=ml_available,
        fair_price=fair_price,
        fair_price_range=fair_price_range,
        reliability=reliability,
        floor=floor,
        floor_blocked=floor_blocked,
        explanation=explanation,
        volatility_30d=volatility_30d,
        demand_index=demand_index,
    )
    logistics_explanation = _build_logistics_explanation(logistics_result)
    final_explanation = _build_final_explanation(
        pricing_explanation=pricing_explanation,
        logistics_explanation=logistics_explanation,
        farmer_payout_per_kg=fair_price,
        logistics_cost_per_kg=logistics_per_kg,
        platform_fee_per_kg=platform_fee_per_kg,
        platform_fee_pct=platform_fee_pct,
        buyer_price_per_kg=buyer_price_per_kg,
        farmer_total=farmer_total,
        logistics_total=logistics_total_calc,
        platform_total=platform_total,
        buyer_total=buyer_total,
    )

    # ------------------------------------------------------------------
    # 8. Vehicle class name (from logistics_result if available)
    # ------------------------------------------------------------------
    vehicle_class = _infer_vehicle_class(logistics_result)

    # ------------------------------------------------------------------
    # 9. Assemble final result
    # ------------------------------------------------------------------
    return {
        # -- identifiers --
        "commodity_id": commodity_id,
        "mandi_id": mandi_id,
        "as_of_date": as_of_date,

        # -- pricing --
        "baseline_price_per_kg": round(baseline, 2),
        "forecast_price_per_kg": ml_forecast,
        "fair_price_per_kg": fair_price,
        "farmer_payout_per_kg": fair_price,

        # -- price range --
        "price_range_low": range_low,
        "price_range_high": range_high,
        "price_range_spread": fair_price_range.get("spread"),

        # -- reliability --
        "reliability_score": reliability,

        # -- farmer protection --
        "protected_floor": floor,
        "floor_blocked": floor_blocked,
        "floor_status": pricing_result.get("floor_status", "OK"),
        "floor_margin": pricing_result.get("floor_margin"),

        # -- logistics --
        "distance_km": round(distance_km, 2),
        "vehicle_class": vehicle_class,
        "vehicle_capacity_kg": logistics_result.get("vehicle_capacity_kg"),
        "required_trips": logistics_result.get("trips"),
        "transport_cost": logistics_result.get("transport_cost"),
        "handling_cost": logistics_result.get("handling_cost"),
        "spoilage_buffer": logistics_result.get("spoilage_buffer"),
        "total_logistics_cost": round(logistics_total_calc, 2),
        "logistics_cost_per_kg": round(logistics_per_kg, 2),

        # -- platform --
        "platform_fee_pct": platform_fee_pct,
        "platform_fee_per_kg": round(platform_fee_per_kg, 2),

        # -- final buyer price --
        "buyer_price_per_kg": round(buyer_price_per_kg, 2),
        "buyer_total": buyer_total,

        # -- quantity --
        "quantity_kg": round(quantity_kg_eff, 2),

        # -- totals --
        "farmer_total": farmer_total,
        "logistics_total": round(logistics_total_calc, 2),
        "platform_total": platform_total,

        # -- fallback --
        "is_fallback": is_fallback,
        "fallback_reason": fallback_reason,

        # -- explanations --
        "pricing_explanation": pricing_explanation,
        "logistics_explanation": logistics_explanation,
        "explanation": final_explanation,
    }


# ---------------------------------------------------------------------------
# Explanation builders
# ---------------------------------------------------------------------------


def _build_pricing_explanation(
    baseline: float,
    ml_forecast: Optional[float],
    ml_available: bool,
    fair_price: float,
    fair_price_range: Dict[str, Any],
    reliability: Optional[int],
    floor: Optional[float],
    floor_blocked: bool,
    explanation: Dict[str, Any],
    volatility_30d: Optional[float],
    demand_index: Optional[float],
) -> Dict[str, Any]:
    """Build the pricing-side explanation section."""
    return {
        "baseline_price_per_kg": round(baseline, 2),
        "forecast_price_per_kg": ml_forecast,
        "ml_available": ml_available,
        "fair_price_per_kg": fair_price,
        "price_range": {
            "low": fair_price_range.get("lower"),
            "high": fair_price_range.get("upper"),
            "spread": fair_price_range.get("spread"),
        },
        "reliability_score": reliability,
        "volatility_30d": volatility_30d,
        "demand_index": demand_index,
        "farmer_protection": {
            "floor_per_kg": floor,
            "blocked": floor_blocked,
            "status": "BLOCKED" if floor_blocked else "OK",
        },
        "forecast_drivers": explanation.get("forecastDrivers", []),
        "pricing_constraints": explanation.get("pricingConstraints", []),
        "fallbacks_used": explanation.get("fallbacksUsed", []),
        "model_version": explanation.get("modelVersion"),
    }


def _build_logistics_explanation(logistics_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build the logistics-side explanation section."""
    return {
        "distance_km": round(float(logistics_result["distance_km"]), 2),
        "is_estimated": logistics_result.get("is_fallback", False),
        "fallback_reason": logistics_result.get("fallback_reason"),
        "vehicle_capacity_kg": logistics_result.get("vehicle_capacity_kg"),
        "required_trips": logistics_result.get("trips"),
        "breakdown": {
            "transport": logistics_result.get("transport_cost", 0),
            "handling": logistics_result.get("handling_cost", 0),
            "spoilage_buffer": logistics_result.get("spoilage_buffer", 0),
        },
        "total_logistics_cost": round(float(logistics_result["total_logistics_cost"]), 2),
        "cost_per_kg": round(float(logistics_result["cost_per_kg"]), 2),
    }


def _build_final_explanation(
    pricing_explanation: Dict[str, Any],
    logistics_explanation: Dict[str, Any],
    farmer_payout_per_kg: float,
    logistics_cost_per_kg: float,
    platform_fee_per_kg: float,
    platform_fee_pct: float,
    buyer_price_per_kg: float,
    farmer_total: float,
    logistics_total: float,
    platform_total: float,
    buyer_total: float,
) -> Dict[str, Any]:
    """Build the combined final explanation payload."""
    return {
        "pricing": pricing_explanation,
        "logistics": logistics_explanation,
        "price_breakdown": {
            "farmer_payout_per_kg": round(farmer_payout_per_kg, 2),
            "logistics_cost_per_kg": round(logistics_cost_per_kg, 2),
            "platform_fee_pct": platform_fee_pct,
            "platform_fee_per_kg": round(platform_fee_per_kg, 2),
            "buyer_price_per_kg": round(buyer_price_per_kg, 2),
        },
        "totals": {
            "farmer_total": farmer_total,
            "logistics_total": logistics_total,
            "platform_total": platform_total,
            "buyer_total": buyer_total,
        },
    }


def _infer_vehicle_class(logistics_result: Dict[str, Any]) -> Optional[str]:
    """Infer vehicle class name from capacity if possible."""
    capacity = logistics_result.get("vehicle_capacity_kg")
    if capacity is None:
        return None
    capacity_map = {
        200: "auto_rickshaw",
        1000: "tempo",
        2500: "mini_truck",
        5000: "truck",
    }
    return capacity_map.get(int(capacity))
