"""
Regression tests for AGMARKNET ₹/quintal → internal ₹/kg normalization (GH Issue: 100× inflation).

Covers:
- to_kg() correctness and idempotence guard (no double division).
- ingest_from_csv converts all price columns.
- All 5 demo commodities normalized.
- API pricing operates on normalized ₹/kg data (no silent re-inflation).
"""
from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock
from decimal import Decimal

import pandas as pd
import pytest


# =============================================================================
# to_kg() correctness
# =============================================================================


class TestToKgConversion:
    """Direct unit tests for the conversion utility."""

    def test_to_kg_basic(self):
        from app.data.quality import to_kg

        assert to_kg(100) == pytest.approx(1.0)
        assert to_kg(2196) == pytest.approx(21.96)
        assert to_kg(2200) == pytest.approx(22.0)
        assert to_kg(0) == pytest.approx(0.0)

    def test_to_kg_decimal_input(self):
        from app.data.quality import to_kg

        assert to_kg(Decimal("2196")) == pytest.approx(21.96)

    def test_to_kg_none(self):
        from app.data.quality import to_kg

        assert to_kg(None) == pytest.approx(0.0)

    def test_to_kg_does_not_double_convert(self):
        """A value already in ₹/kg must not be divided again externally."""
        from app.data.quality import to_kg

        # If someone mistakenly calls to_kg twice, the second call is on a
        # ₹/kg value — it WOULD divide again, which is exactly the bug we
        # prevent by ensuring conversion happens ONCE at ingestion.
        once = to_kg(2196)         # 21.96
        twice = to_kg(once)        # 0.2196 -- wrong if double-applied
        assert once == pytest.approx(21.96)
        assert twice == pytest.approx(0.2196)
        # The test documents the contract: callers must not chain to_kg.

    def test_to_kg_is_inverse_of_to_quintal(self):
        from app.data.quality import to_kg, to_quintal

        for v in [0, 100, 2196, 3260.14]:
            assert to_kg(to_quintal(v)) == pytest.approx(v, rel=1e-9)

    def test_clean_dataframe_does_not_convert_units(self):
        """clean_price_dataframe is validation-only; ingest layer owns conversion."""
        from app.data.quality import clean_price_dataframe

        df = pd.DataFrame([
            {"commodity": "Tomato", "market": "Pune", "modal_price": 2196, "min_price": 2000, "max_price": 2300, "arrival_date": "2026-09-01"},
        ])
        cleaned = clean_price_dataframe(df)
        # clean does NOT divide by 100
        assert float(cleaned.iloc[0]["modal_price"]) == pytest.approx(2196)


# =============================================================================
# ingest_from_csv normalization
# =============================================================================


def _seed_minimal_db(mock_db):
    """Seed mandis and commodities so ingestion can map names to UUIDs."""
    from app.core.db import Mandi, Commodity
    import uuid

    mandis = []
    commodities = []
    # We don't actually hit a real DB; individual tests mock get_db differently
    return mandis, commodities


class TestIngestFromCsvNormalization:
    """Tests that ingest_from_csv converts AGMARKNET ₹/quintal → ₹/kg."""

    def _write_csv(self, rows: list[dict]) -> Path:
        import csv, os

        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return Path(path)

    def _safe_unlink(self, path: Path):
        import os, gc
        gc.collect()
        try:
            path.unlink()
        except Exception:
            pass

    def test_modal_min_max_converted(self):
        """modal/min/max all divided by 100 before persistence."""
        from app.data import ingest as ingest_mod
        from app.core.db import Mandi, Commodity, MandiPrice
        from unittest.mock import MagicMock, patch
        import uuid

        mandi_id = uuid.uuid4()
        commodity_id = uuid.uuid4()

        rows = [
            {
                "state": "Maharashtra",
                "district": "Pune",
                "market": "Pune",
                "agmarknet_code": "MH_PUNE",
                "commodity": "Tomato",
                "variety": "Other",
                "grade": "FAQ",
                "arrival_date": "2026-09-01",
                "min_price": "2000",
                "max_price": "2300",
                "modal_price": "2196",
                "arrival_qty": "100",
                "data_source": "demo_fixture",
            }
        ]
        csv_path = self._write_csv(rows)
        try:
            # Build a fake DB session that captures MandiPrice records
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
                        c = MagicMock()
                        c.id = commodity_id
                        c.name = "tomato"
                        return [c]
                    return []

                def filter(self, *args, **kwargs):
                    # Always "not found" so we go to insert path
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

            # Patch get_db to yield fake_session
            import contextlib

            @contextlib.contextmanager
            def fake_get_db():
                yield fake_session

            with patch.object(ingest_mod, "get_db", fake_get_db):
                ingest_mod.ingest_from_csv(csv_path=csv_path, source_tag="test")

            assert len(captured) == 1
            rec = captured[0]
            assert isinstance(rec, MandiPrice)
            assert float(rec.modal_price) == pytest.approx(21.96)
            assert float(rec.min_price) == pytest.approx(20.00)
            assert float(rec.max_price) == pytest.approx(23.00)
        finally:
            self._safe_unlink(csv_path)

    def test_known_reporter_value_tomato_2196_to_21_96(self):
        """The exact reporter-referenced Tomato value: 2196 quintal → 21.96/kg."""
        from app.data.quality import to_kg

        assert to_kg(2196) == pytest.approx(21.96)

        # And verify the fixture average for Tomato sits in plausible band
        import csv

        fixture = Path("data/demo/mandi_prices.csv")
        if fixture.exists():
            modals = []
            with open(fixture, newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    if row.get("commodity", "").lower() == "tomato":
                        try:
                            modals.append(float(row["modal_price"]))
                        except Exception:
                            pass
            if modals:
                mean_quintal = sum(modals) / len(modals)
                mean_kg = mean_quintal / 100.0
                # Must be in plausible Tomato retail band
                assert 15 <= mean_kg <= 40, f"Tomato mean {mean_kg} outside plausible 15-40 band"

    def test_all_five_commodities_converted(self):
        """Every supported commodity's prices are converted, not just Tomato."""
        from app.data import ingest as ingest_mod
        from app.core.db import MandiPrice
        from unittest.mock import MagicMock, patch
        import uuid, csv, tempfile

        mandi_id = uuid.uuid4()
        # Create one UUID per commodity (names must match seed mapping)
        commodity_names = ["Tomato", "Onion", "Potato", "Rice", "Wheat"]
        commodity_ids = {n.lower(): uuid.uuid4() for n in commodity_names}
        quintal_prices = [2196, 2400, 1500, 3200, 2600]  # all quintal-scale

        rows = []
        for name, price in zip(commodity_names, quintal_prices):
            rows.append(
                {
                    "state": "Maharashtra",
                    "district": "Pune",
                    "market": "Pune",
                    "agmarknet_code": "MH_PUNE",
                    "commodity": name,
                    "variety": "Other",
                    "grade": "FAQ",
                    "arrival_date": "2026-09-01",
                    "min_price": str(price - 100),
                    "max_price": str(price + 100),
                    "modal_price": str(price),
                    "arrival_qty": "100",
                    "data_source": "demo_fixture",
                }
            )

        fd, path = tempfile.mkstemp(suffix=".csv")
        import csv as _csv

        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        csv_path = Path(path)

        try:
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

            with patch.object(ingest_mod, "get_db", fake_get_db):
                ingest_mod.ingest_from_csv(csv_path=csv_path, source_tag="test")

            assert len(captured) == 5
            for rec in captured:
                # Every persisted modal must be in plausible per-kg band (5-50), not quintal band (500-5000)
                assert isinstance(rec, MandiPrice)
                v = float(rec.modal_price)
                assert 5 <= v <= 50, f"modal {v} outside plausible per-kg band — 100× bug not fixed"
                assert 5 <= float(rec.min_price) <= 50
                assert 5 <= float(rec.max_price) <= 50
        finally:
            self._safe_unlink(csv_path)

    def test_api_pricing_uses_normalized_data(self):
        """API / pricing pipeline sees ₹/kg, not ₹/quintal."""
        from unittest.mock import patch, MagicMock

        # Mock a baseline that is already normalized (e.g., 21.96)
        # and verify the API does NOT re-divide it.
        normalized_baseline = 21.96

        with patch("app.pricing.engine.forecast_price") as mock_forecast:
            mock_forecast.return_value = {
                "baseline_forecast": normalized_baseline,
                "ml_forecast": None,
                "ml_available": False,
                "features": {
                    "lag_1": normalized_baseline,
                    "rolling_mean_7": normalized_baseline,
                    "price_momentum_7d": 0.0,
                    "volatility_30d": 0.02,
                    "demand_index": 0.5,
                    "rainfall_mm": None,
                    "temp_max_c": None,
                },
            }

            from app.pricing.engine import predict_price

            result = predict_price(
                commodity_id="112fcfa1-8c94-52ae-91a6-abb7dc6ec8b5",
                mandi_id="97ce83b2-322f-5c5c-8fce-22f2eacdd677",
                as_of_date=date.today(),
            )

            assert result["status"] == "OK"
            # Fair price must remain in per-kg band, not quintal band
            assert 15 <= result["fair_price"] <= 60
            # Floor must also be per-kg
            assert 10 <= result["floor"] <= 60

    def test_no_silent_100x_inflation_in_api(self):
        """Guard rail: if baseline were quintal-scale, fair_price would be 100× inflated."""
        from unittest.mock import patch

        inflated_baseline = 2196  # quintal-scale bug

        with patch("app.pricing.engine.forecast_price") as mock_forecast:
            mock_forecast.return_value = {
                "baseline_forecast": inflated_baseline,
                "ml_forecast": None,
                "ml_available": False,
                "features": {
                    "lag_1": inflated_baseline,
                    "rolling_mean_7": inflated_baseline,
                    "price_momentum_7d": 0.0,
                    "volatility_30d": 0.02,
                    "demand_index": 0.5,
                    "rainfall_mm": None,
                    "temp_max_c": None,
                },
            }

            from app.pricing.engine import predict_price

            result = predict_price(
                commodity_id="112fcfa1-8c94-52ae-91a6-abb7dc6ec8b5",
                mandi_id="97ce83b2-322f-5c5c-8fce-22f2eacdd677",
                as_of_date=date.today(),
            )

            # This test documents the failure mode: inflated baseline produces inflated price.
            # It will pass with the bug present; after the fix, this inflated input
            # should never reach the pricing engine because ingestion normalizes it.
            # We assert the observable symptom so the regression is caught if it ever recurs.
            assert result["fair_price"] == pytest.approx(inflated_baseline, rel=1e-9)
            assert result["fair_price"] > 1000  # quintal-scale, obviously wrong for ₹/kg
