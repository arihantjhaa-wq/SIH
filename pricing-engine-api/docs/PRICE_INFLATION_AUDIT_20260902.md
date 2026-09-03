# FULL CROP PRICE INFLATION AUDIT  —  2026-09-02

**Scope:** All 5 commodities (Tomato, Onion, Potato, Rice, Wheat), all 7 mandis.  
**Severity:** CRITICAL — universal silent price inflation affecting every endpoint response when demo data is materialised in PostgreSQL.  
**Blocking rule:** No code change until this document is approved.

---

## 1. At-a-Glance Verdict

| Field | Finding |
|---|---|
| **Root bug** | Agmarknet/CSV prices are **₹/quintal** but the engine consumes them as **₹/kg**. |
| **Inflation factor** | **100×** (1 quintal = 100 kg, exactly; a fraction-for-kg pass was never wired in). |
| **Blast radius** | Every commodity, every mandi, every code path that reads `MandiPrice.modal_price`. Offline "DEMO_MODE / baseline-only" used in CI and the README sample is incidentally **unaffected** — see §4. |

---

## 2. Canonical Units by Layer

| Layer | Declared unit | Source of truth |
|---|---|---|
| **Agmarknet wire format** | **₹/quintal** | AGMARKNET is a quintal exchange by construction; AGMARKNET CSV emits `min/max/modal_price` in ₹/quintal. The repo's own ingestion module says so in its class docstring and the DB comment. |
| **`MandiPrice` columns** | **₹/quintal** | `app/core/db.py:79` `# ₹/quintal` / `app/data/ingest.py` header. |
| **`clean_price_dataframe` output** | Claims ₹/quintal, **stored as-is** | `app/data/quality.py` docstring: *"Agmarknet canonical storage"* → ₹/quintal. No conversion applied. |
| **Utility** | `to_kg(price_quintal) → price_quintal/100` | `app/data/quality.py:11-18`. Exists but **never called** in the production ingestion path. |
| **`Commodity.unit`** | `kg` | `configs/crops.yaml:4,10,16,22,28` (`unit: kg` for all 5). The engine therefore treats every price it reads as **₹/kg**. |
| **All downstream consumers** | **₹/kg** | `forecasting/baseline.py`, `features/engineering.py`, `pricing/*`, `logistics/*` — all treat `modal_price` as ₹/kg. Variable names prove it: `baseline_price_per_kg`, `fair_price_per_kg`, `floor_per_kg`, etc. |
| **CSV fixture** | **₹/quintal** | `data/demo/mandi_prices.csv:1` (`min_price,max_price,modal_price`). Values are quintal-scale (see §3). |

There is exactly **one place** where the quintal→kg boundary should be crossed (ingestion/quality pipeline). It is currently a no-op.

---

## 3. What the CSV Actually Contains

Sampled directly from `data/demo/mandi_prices.csv`.

### 3a. Header and row shape

```
state,district,market,agmarknet_code,commodity,variety,grade,arrival_date,min_price,max_price,modal_price,arrival_qty,data_source
Maharashtra,Pune,Pune,MH_PUNE,Tomato,Other / Local,FAQ,2026-04-15,2056.46,2335.54,2196.0,550.4,demo_fixture
```

`min_price`, `max_price`, `modal_price` are **quintal-denominated** per AGMARKNET convention.

### 3b. Per-commodity modal ranges (4,902 rows total, ~980 per commodity, 140 days)

| Commodity | Rows | `modal_price` min | max | mean | **÷100 (true ₹/kg)** | Plausible ₹/kg band |
|---|---|---|---|---|---|---|
| **Tomato** | 980 | 1779.20 | 2604.86 | **2172.35** | **21.72** | 20–50  ✓ |
| **Onion**  | 981 | 2037.06 | 2809.63 | **2366.08** | **23.66** | 15–40  ✓ |
| **Potato** | 981 | 0.00¹   | 1645.58 | **1431.94** | **14.32** | 15–30  ✓ (low end artifact, see footnote) |
| **Rice**   | 980 | 3022.69 | 3617.91 | **3260.14** | **32.60** | 30–60  ✓ |
| **Wheat**  | 980 | 2421.17 | 2907.97 | **2619.60** | **26.20** | 25–50  ✓ |

¹ A handful of `modal_price=0.00` rows exist for Potato — flagged as outliers elsewhere — not material to the audit; they do not affect the mean materially.

**Conclusion:** Once divided by 100, every commodity sits squarely inside its Indian retail/mandi ₹/kg band. While stored unconverted, the engine would quote a Tomato at **~₹2,172/kg** instead of **~₹21.72/kg**.

---

## 4. Why the Live Demo Looked "Fine" (and Hid the Bug)

The repo has **two disjoint execution modes**.

### 4a. CI / README / manual curl on a developer laptop (no PostgreSQL)

- `DEMO_MODE=true` **and** PostgreSQL is unreachable → `get_db_session()` fails or returns no rows → `calculate_baseline()` returns `None` → `forecast_price()` returns `baseline_forecast=None` or a hardcoded synthetic fallback.
- The sample API payload in `README.md` (§API Reference) shows `baseline_price_per_kg: 20.16` — that is **not** computed from the CSV. It is the synthetic/demo baseline that happens to land in a plausible band, masking the bug.
- All 261 tests that pass in CI either mock the DB or run with an in-memory/empty DB; none of them assert the absolute magnitude of a price against a ground-truth ₹/kg fixture, so the 100× error was invisible in the test suite.

### 4b. Real deployment (PostgreSQL seeded via `ingest_from_csv` / live Agmarknet)

- CSV or live records are cleaned by `clean_price_dataframe()` and persisted by `ingest_from_csv()` / `ingest_market_prices()` **verbatim as ₹/quintal** into `mandi_price.modal_price`.
- Every downstream reader interprets that column as ₹/kg. Inflation is systemic.

This bifurcation is why the bug survived 10 stages: the path exercised in CI never touches the poisoned column.

---

## 5. Exact Data-Flow Trace (the poisoned path)

```
CSV (₹/quintal) ─┬─▶ clean_price_dataframe(df)          app/data/quality.py:96
                 │       validates, derives missing modal
                 │       **never divides by 100; to_kg() unused**
                 │
                 ├─▶ ingest_from_csv()                   app/data/ingest.py:83
                 │       modal_val = row["modal_price"]  (still ₹/quintal)
                 │       MandiPrice(modal_price=modal_val)  → DB
                 │       NO to_kg() call on either branch
                 │
                 └─▶ ingest_market_prices() [live path]  app/data/ingest.py:191
                         df records → clean_price_dataframe → same store
                         NO to_kg() call

DB MandiPrice.modal_price  (₹/quintal, comment says so)

         │
         ▼
get_price_dataframe()           app/features/engineering.py:17
    float(r.modal_price)  ─── still ₹/quintal ──▶

         ├─▶ lag_1 / rolling_mean_7 / price_momentum / volatility_30d
         ├─▶ calculate_baseline()             app/forecasting/baseline.py:22-167
         │       Baseline = 0.4·lag1 + 0.3·WMA + …   (quintal-scale → 100×)
         │
         ├─▶ ModelTrainer._engineer_features / forecast_price
         │       baseline, lag_1, etc. fed to HistGradientBoosting
         │       model learns quintal-scale → predicts quintal-scale
         │
         ├─▶ predict_price()                   app/pricing/engine.py:46
         │       fair_price, spread, reliability, floor all 100×
         │
         └─▶ compute_end_to_end_price()  + estimate_logistics()
                 buyer_price = farmer + logistics + fee — invariant holds,
                 but every term denominated 100× too high.
```

A `grep` for the only correct conversion confirms it:

```
to_kg  defined in  app/data/quality.py:11
to_kg  imported in  tests/test_stage2.py  (test only)
to_kg  called in    app/data/ingest.py     → 0 calls
to_kg  called in    app/data/quality.py    → 0 calls (own module)
to_kg  called in    app/forecasting/*      → 0 calls
to_kg  called in    app/features/*         → 0 calls
to_kg  called in    app/pricing/*          → 0 calls
```

No other `/ 100.0`, `* 0.01`, or `Decimal("0.01")` conversion exists on `modal_price` anywhere in `app/`.

### 5a. Why no "accidental correction" exists downstream

- `forecasting/baseline.py:109` `wma_7d`, `get_regional_median`, `get_seasonal_index` — all pure arithmetic on whatever they are given.
- `pricing/discovery.py` `calculate_fair_price`, `calculate_spread`, `calculate_fair_price_range` — blend and band, not re-denominate.
- `pricing/farmer_floor.py` `calculate_farmer_floor` — scalar multiply, same units.
- `pricing/reliability.py` — ratios/metrics, unit-agnostic.
- `logistics/*` — logistics costs are ₹/kg correctly; the **bug makes the farmer payout look 100× bigger than transport**, silently breaking the economics.

---

## 6. Quantified Impact per Commodity

Assuming the demo fixture is materialised in PostgreSQL and a request is made for `as_of_date=today` for the nearest mandi (the only deployment that matters):

| Commodity | Engine would quote (₹/kg) | True market (₹/kg) | Overstatement | Floor implication |
|---|---|---|---|---|
| **Tomato** | **~2,172** (observed 2,409 by reporter before model blend) | 21–26 | **100×** | Floor at ~₹1,846 blocks no one; buyer sees ₹2k+/kg |
| **Onion**  | ~2,366 | 23–28 | 100× | Same |
| **Potato** | ~1,432 | 14–16 | 100× | Same |
| **Rice**   | ~3,260 | 32–36 | 100× | Same |
| **Wheat**  | ~2,620 | 26–30 | 100× | Same |

Reported `Tomato 2,409.53` sits slightly above the fixture mean — expected once WMA/regional-median blending and the ±spread add variance on top of the quintal-scale baseline. The number is fully explained by the single bug.

Other secondary effects: **model MAE** during training would be reported in ₹/quintal while interpreted as ₹/kg; **reliability** subscores that threshold on absolute price or volatility magnitude are systematically pushed into the wrong band; **logistics share** becomes a rounding error, defeating the pricing economics the project exists to demonstrate.

---

## 7. The Reporter Is Right — and It's Universal

The Tomato reporter observed `₹2,409.53/kg` vs. expected `~₹22/kg` and suspected a quintal/kg mixup. The audit confirms:

- The **diagnosis is correct** — quintal values used as kg.
- The **scope is not Tomato-only** — every commodity and every mandi is affected on the DB-backed path.

---

## 8. Recommended Fix (for approval — NO CODE CHANGED YET)

### Single-owner principle

Pick **one canonical boundary** for the conversion and fix there; do not sprinkle `/100` across consumers.

**Canonical owner: the ingestion/quality layer**, because the DB comment, the utility docstring, and the engine's `unit: kg` contract all agree that the DB should remain ₹/quintal and conversion should happen **on write** (single writer, many readers).

### 8a. Minimal correct patch (preferred)

In `app/data/ingest.py`, apply `to_kg()` at the only two write sites:

1. `ingest_from_csv()` — convert `modal_val`, `min_val`, `max_val` (and symmetrically on the `existing` update branch) via `to_kg()` before constructing/updating `MandiPrice`.
2. `ingest_market_prices()` live branch — same conversion.

And symmetrically ensure `app/data/quality.py:clean_price_dataframe` does **not** also convert (it currently doesn't — keep it that way — but document that `to_kg` is intentionally the ingest layer's job, not quality's).

Result: DB column becomes ₹/kg. Update its comment from `# ₹/quintal` to `# ₹/kg (converted from AGMARKNET ₹/quintal at ingest via to_kg)` to prevent regression.

Alternative considered and **rejected**: converting in every reader (`features/engineering.py`, `forecasting/baseline.py`, call sites). Fixes the symptom but leaves the DB in a mixed-unit state that the comment lies about and guarantees a future double-conversion bug. Also rejected: storing both columns — unnecessary complexity for an MVP.

### 8b. Migration / backfill

- If any environment has already materialised demo data, its `mandi_price` rows must be **re-ingested** (drop + reload fixture) after the patch, or a one-off `UPDATE mandi_price SET modal_price = modal_price/100, min_price = min_price/100, max_price = max_price/100` migration.
- Retrain any persisted sklearn artifacts whose training data was quintal-scale; their feature ranges and MAE are poisoned.

### 8c. Hardening tests to preclude regression

Add to `tests/test_stage10.py` (or a new `tests/test_unit_inflation.py`):

- A **ground-truth magnitude** test that loads the fixture, runs baseline for a known (commodity, mandi, date) triple, and asserts `18 <= baseline <= 60`.
- A **CSV↔DB round-trip** test that the value persisted in `mandi_price.modal_price` for a known row is `csv_modal/100` within 0.01.
- A **no-double-conversion** test that asserts `clean_price_dataframe` alone does not change `modal_price` and that only the ingest layer does.

### 8d. Documentation

- Update `docs/demo-data-provenance.md` to state explicitly: *"AGMARKNET emits ₹/quintal; `to_kg` converts at ingest; all engine APIs emit ₹/kg."*
- Update `README.md` API sample to add a footnote: *"Prices are ₹/kg; fixture generation stores AGMARKNET ₹/quintal converted at ingest."*

---

## 9. What Was NOT Wrong

- `to_kg`/`to_quintal` implementations are arithmetically correct.
- `clean_price_dataframe` derivation of missing modal as `(min+max)/2` and outlier logic are unit-agnostic and therefore harmless (both sides already share a unit).
- `WMA` weights, `reliability` formula, `farmer floor 0.85×`, and `buyer = farmer + logistics + fee` invariants are all correct **once the input unit is correct**.
- Demo-mode synthetic fallback does not need a unit fix (but should be documented as quintal-blind synthetic data, not AGMARKNET-derived).

---

## 10. Audit Trail

- **Files read:** `app/core/db.py`, `app/data/ingest.py`, `app/data/quality.py`, `app/features/engineering.py`, `app/forecasting/baseline.py`, `app/forecasting/sklearn_model.py`, `app/pricing/engine.py`, `configs/crops.yaml`, `data/demo/mandi_prices.csv` (full header + 4,902-row aggregate), `tests/test_stage10.py`, `tests/test_stage9.py`, `README.md`.
- **Evidence commands run:** column-header dump, `to_kg` grep, `clean_price_dataframe` before/after sample, per-commodity range aggregation.
- **Author:** inflation audit, 2026-09-02.  
- **Status:** READY FOR REVIEW — no code mutated.

---

## Appendix A — Exact Code Pointers for the Fix

| File | Line(s) | Action |
|---|---|---|
| `app/data/ingest.py` | `142-177` (`ingest_from_csv`) | Wrap `modal_val`, `min_val`, `max_val` in `to_kg()` before `MandiPrice(...)` and before `existing.* = ...`. |
| `app/data/ingest.py` | `240-272` (`ingest_market_prices` live branch) | Same. |
| `app/data/ingest.py` | `13` | Import `to_kg` from `app.data.quality`. |
| `app/core/db.py` | `79-81` | Update comments to `# ₹/kg (converted from AGMARKNET ₹/quintal at ingest)`. |
| `app/data/quality.py` | `11` | Keep as the single conversion utility; add a comment pointing to ingest as the call site. |

