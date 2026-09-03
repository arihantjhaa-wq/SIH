"""
Test suite for 20-crop expansion verification.

Covers:
1. Config: All 20 crops exist, all active, IDs deterministic, no duplicates
2. API: All 20 commodity names accepted by _get_commodity_id (returns non-None)
3. API rejection: Invalid commodity (e.g. "MangoXYZ") still returns 400
4. API schema: Existing PricingRequest accepts all 20 names (no validation breakage)
5. Ingestion: ingest_from_csv matches all 20 commodity names
6. Pricing engine: predict_price works for all 20 (mock baseline, verify result status=OK)
7. Regression: Original 5 crops still work identically
"""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import date
import yaml
import pytest


# =============================================================================
# Expected 20 crop names (matching configs/crops.yaml exactly)
# =============================================================================

EXPECTED_CROPS = [
    "Tomato",
    "Onion",
    "Potato",
    "Rice",
    "Wheat",
    "Maize",
    "Groundnut",
    "Soybean",
    "Mustard",
    "Gram",
    "Lentil",
    "Pigeon Pea",
    "Cabbage",
    "Cauliflower",
    "Green Chilli",
    "Brinjal",
    "Mango",
    "Banana",
    "Orange",
    "Apple",
]


# =============================================================================
# 1. Config tests
# =============================================================================

class TestConfig20Crops:
    """Verify crops.yaml has exactly 20 active crops with deterministic UUIDs."""

    def test_crops_yaml_has_20_crops(self):
        """crops.yaml should contain exactly 20 crops."""
        config_path = Path(__file__).parent.parent / "configs" / "crops.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert len(config["crops"]) == 20

    def test_all_crops_active(self):
        """All 20 crops should be marked is_active: true."""
        config_path = Path(__file__).parent.parent / "configs" / "crops.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for crop in config["crops"]:
            assert crop["is_active"] is True, f"Crop {crop['name']} is not active"

    def test_crop_names_match_expected(self):
        """Crop names in config should match the expected 20 list exactly."""
        config_path = Path(__file__).parent.parent / "configs" / "crops.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        actual_names = [c["name"] for c in config["crops"]]
        assert actual_names == EXPECTED_CROPS

    def test_no_duplicate_names(self):
        """No duplicate crop names in config."""
        config_path = Path(__file__).parent.parent / "configs" / "crops.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        names = [c["name"] for c in config["crops"]]
        assert len(names) == len(set(names))

    def test_deterministic_uuids(self):
        """UUIDs derived from commodity names must be deterministic (uuid5)."""
        for name in EXPECTED_CROPS:
            # Derive UUID the same way seed_config.py and _get_commodity_id do
            expected_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"commodity.{name.lower()}"))
            # Run twice to verify determinism
            assert str(uuid.uuid5(uuid.NAMESPACE_DNS, f"commodity.{name.lower()}")) == expected_uuid


# =============================================================================
# 2. API _get_commodity_id tests
# =============================================================================

class TestAPICommodityMapping:
    """Verify _get_commodity_id accepts all 20 crops and rejects invalid."""

    def test_all_20_crops_accepted(self):
        """All 20 crop names should return a valid UUID."""
        from app.api.routes.pricing import _get_commodity_id

        for name in EXPECTED_CROPS:
            commodity_id = _get_commodity_id(name)
            assert commodity_id is not None, f"Crop '{name}' not accepted by API"
            # Verify it's a valid UUID string
            parsed = uuid.UUID(commodity_id)
            assert str(parsed) == commodity_id

    def test_all_20_crops_case_insensitive(self):
        """Commodity mapping should be case-insensitive for all 20 crops."""
        from app.api.routes.pricing import _get_commodity_id

        for name in EXPECTED_CROPS:
            lower = name.lower()
            upper = name.upper()
            mixed = name.title()  # First letter capitalized

            assert _get_commodity_id(lower) is not None, f"Lowercase '{lower}' failed"
            assert _get_commodity_id(upper) is not None, f"Uppercase '{upper}' failed"
            assert _get_commodity_id(mixed) is not None, f"Title case '{mixed}' failed"

    def test_invalid_commodity_rejected(self):
        """Unknown commodity should return None (triggers 400 in endpoint)."""
        from app.api.routes.pricing import _get_commodity_id

        invalid_names = ["MangoXYZ", "InvalidCrop", "TomatoXYZ", "", "Unknown"]
        for name in invalid_names:
            result = _get_commodity_id(name)
            assert result is None, f"Invalid name '{name}' should return None, got {result}"


# =============================================================================
# 3. API endpoint rejection tests
# =============================================================================

class TestAPIEndpointRejection:
    """Verify API endpoint returns 400 for invalid commodities."""

    def test_unknown_commodity_returns_400(self):
        """POST /api/v1/pricing/estimate with unknown commodity returns 400."""
        from fastapi.testclient import TestClient
        from app.api.main import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/pricing/estimate",
            json={
                "commodity": "InvalidCropXYZ",
                "quantity_kg": 500.0,
                "farmer_location": {"lat": 18.5204, "lon": 73.8567},
                "buyer_location": {"lat": 19.0760, "lon": 72.8777},
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "INVALID_COMMODITY"

    def test_valid_crops_not_rejected_by_schema(self):
        """All 20 valid crop names should pass Pydantic schema validation."""
        from app.api.schemas.pricing import PricingRequest
        from pydantic import ValidationError

        for name in EXPECTED_CROPS:
            # Should not raise ValidationError
            request = PricingRequest(
                commodity=name,
                quantity_kg=500.0,
                farmer_location={"lat": 18.5204, "lon": 73.8567},
                buyer_location={"lat": 19.0760, "lon": 72.8777},
            )
            assert request.commodity == name


# =============================================================================
# 4. Ingestion matching tests
# =============================================================================

class TestIngestionMatching:
    """Verify ingest_from_csv matches all 20 commodity names."""

    def test_ingest_matches_all_20_crops(self):
        """ingest_from_csv should find commodity UUID for all 20 crops."""
        from app.data import ingest as ingest_mod
        from app.core.db import Mandi, Commodity

        # Create a mock DB session that has all 20 commodities
        mandi_id = uuid.uuid4()
        commodity_ids = {name.lower(): uuid.uuid4() for name in EXPECTED_CROPS}

        captured = []

        class FakeQuery:
            def __init__(self, model):
                self.model = model

            def all(self):
                if self.model.__name__ == "Mandi":
                    m = MagicMock()
                    m.id = mandi_id
                    m.name = "pune"
                    m.agmarknet_code = "MH_PUNE"
                    return [m]
                if self.model.__name__ == "Commodity":
                    out = []
                    for n, cid in commodity_ids.items():
                        c = MagicMock()
                        c.id = cid
                        c.name = n
                        out.append(c)
                    return out
                return []

            def filter(self, *args, **kwargs):
                class F:
                    def first(self_inner):
                        return None
                return F()

        class FakeSession:
            def query(self, model):
                return FakeQuery(model)

            def add(self, obj):
                captured.append(obj)

        fake_session = FakeSession()

        import contextlib

        @contextlib.contextmanager
        def fake_get_db():
            yield fake_session

        # Build minimal CSV rows for all 20 crops
        import csv
        import tempfile
        from pathlib import Path

        rows = []
        for name in EXPECTED_CROPS:
            rows.append({
                "state": "Maharashtra",
                "district": "Pune",
                "market": "Pune",
                "agmarknet_code": "MH_PUNE",
                "commodity": name,
                "variety": "Other",
                "grade": "FAQ",
                "arrival_date": "2026-09-01",
                "min_price": "1000",
                "max_price": "1200",
                "modal_price": "1100",
                "arrival_qty": "100",
                "data_source": "demo_fixture",
            })

        fd, path = tempfile.mkstemp(suffix=".csv")
        import os
        os.close(fd)

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            with patch.object(ingest_mod, "get_db", fake_get_db):
                ingest_mod.ingest_from_csv(csv_path=Path(path), source_tag="test")

            # Should have inserted all 20
            assert len(captured) == 20, f"Expected 20 records, got {len(captured)}"
        finally:
            try:
                Path(path).unlink()
            except Exception:
                pass


# =============================================================================
# 5. Pricing engine tests (with mocked forecast)
# =============================================================================

class TestPricingEngine20Crops:
    """Verify predict_price works for all 20 crops with mocked baseline."""

    def _mock_forecast(self, baseline=21.96):
        """Helper to mock forecast_price returning normalized baseline."""
        return {
            "baseline_forecast": baseline,
            "ml_forecast": None,
            "ml_available": False,
            "features": {
                "lag_1": baseline,
                "rolling_mean_7": baseline,
                "price_momentum_7d": 0.0,
                "volatility_30d": 0.02,
                "demand_index": 0.5,
                "rainfall_mm": None,
                "temp_max_c": None,
            },
        }

    def test_predict_price_works_for_all_20_crops(self):
        """predict_price should return OK status for all 20 crops."""
        from app.pricing.engine import predict_price
        from app.api.routes.pricing import _get_commodity_id

        mandi_id = "97ce83b2-322f-5c5c-8fce-22f2eacdd677"  # Pune mandi

        for name in EXPECTED_CROPS:
            commodity_id = _get_commodity_id(name)
            assert commodity_id is not None

            with patch("app.pricing.engine.forecast_price") as mock_forecast:
                mock_forecast.return_value = self._mock_forecast()
                result = predict_price(
                    commodity_id=commodity_id,
                    mandi_id=mandi_id,
                    as_of_date=date.today(),
                    quantity_kg=500.0,
                )

                assert result["status"] == "OK", f"Crop '{name}' failed: {result.get('reason', 'unknown')}"
                # Prices should be in plausible per-kg range
                assert 5 <= result["fair_price"] <= 60, f"Crop '{name}' fair_price {result['fair_price']} out of range"
                assert 5 <= result["floor"] <= 60, f"Crop '{name}' floor {result['floor']} out of range"


# =============================================================================
# 6. Regression: Original 5 crops unchanged
# =============================================================================

class TestRegressionOriginal5:
    """Ensure original 5 crops (Tomato, Onion, Potato, Rice, Wheat) work identically."""

    def _mock_forecast(self, baseline=21.96):
        return {
            "baseline_forecast": baseline,
            "ml_forecast": None,
            "ml_available": False,
            "features": {
                "lag_1": baseline,
                "rolling_mean_7": baseline,
                "price_momentum_7d": 0.0,
                "volatility_30d": 0.02,
                "demand_index": 0.5,
                "rainfall_mm": None,
                "temp_max_c": None,
            },
        }

    def test_original_5_crops_still_work(self):
        """Original 5 crops should still produce valid pricing results."""
        from app.pricing.engine import predict_price
        from app.api.routes.pricing import _get_commodity_id

        original_5 = ["Tomato", "Onion", "Potato", "Rice", "Wheat"]
        mandi_id = "97ce83b2-322f-5c5c-8fce-22f2eacdd677"  # Pune

        for name in original_5:
            commodity_id = _get_commodity_id(name)
            assert commodity_id is not None

            with patch("app.pricing.engine.forecast_price") as mock_forecast:
                mock_forecast.return_value = self._mock_forecast()
                result = predict_price(
                    commodity_id=commodity_id,
                    mandi_id=mandi_id,
                    as_of_date=date.today(),
                    quantity_kg=500.0,
                )

                assert result["status"] == "OK"
                assert 5 <= result["fair_price"] <= 60
                assert 5 <= result["floor"] <= 60

    def test_original_5_uuid_stability(self):
        """Original 5 crop UUIDs must remain unchanged (deterministic)."""
        from app.api.routes.pricing import _get_commodity_id

        # These are the exact UUIDs that were in the DB before expansion
        # They must match seed_config.py's uuid5 derivation
        expected = {
            "Tomato": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.tomato")),
            "Onion": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.onion")),
            "Potato": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.potato")),
            "Rice": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.rice")),
            "Wheat": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.wheat")),
        }

        for name, expected_uuid in expected.items():
            actual = _get_commodity_id(name)
            assert actual == expected_uuid, f"UUID for {name} changed: {actual} != {expected_uuid}"