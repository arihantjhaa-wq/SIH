# AGRI-DIRECT PRICING ENGINE — INTERNAL HACKATHON MVP
## Antigravity AI Agent Execution Protocol & Stage Prompts

Companion to the MVP Scope and Roadmap documents. These prompts are written to be pasted directly into Antigravity IDE's agentic coding interface, one stage at a time.

---

## Agent Rules (apply to every stage)

The AI agent MUST:
1. Read `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-SCOPE.md` and the current stage's section of `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-ROADMAP.md` before writing any code.
2. Inspect the existing repository state before modifying anything — never assume a file's current contents.
3. Never redesign the architecture, database schema, or pricing formulas without explicitly flagging the discrepancy to the developer and pausing for confirmation.
4. Work only on the scope of the current stage — do not pull work forward from a later stage, even if it seems convenient.
5. Make small, reviewable changes; commit after each successful stage with a `[Stage N]`-prefixed message.
6. Write or update tests alongside implementation, then run the full test suite (not just new tests).
7. Report exactly what passed/failed after every change — never silently modify or skip a failing test to make it pass; report the failure and propose a fix instead.
8. Never fabricate external API field names or response shapes — if the real Agmarknet/weather response hasn't been captured yet, ask the developer to confirm it (V0.1 §4.2's mapping table can be reused directly for Agmarknet fields — the MVP does not need to re-verify it).
9. Clearly label all demo/synthetic data (`dataSource: "demo_fixture"`) wherever it appears in code, logs, or dashboard output — never let synthetic data look identical to a live result.
10. Confirm nothing from a previous stage broke (backward compatibility) before considering the current stage done.

---

## STAGE 0 — Environment + Repository Verification

**Objective:** confirm the local machine is ready before any code is written.

**Files/modules:** none (no code yet).

**Implementation instructions:**
```
Verify the following and report status for each:
1. `python --version` is 3.11 or higher.
2. `docker --version` succeeds and Docker Desktop is running.
3. `git --version` succeeds.
4. The working directory is empty or explicitly confirmed as the intended project root.
Do not proceed to Stage 1 until all four are confirmed. If any check fails,
report exactly what is missing and stop — do not attempt to install system-level
software without explicit developer approval.
```

**Tests:** none (environment check only).

**Acceptance criteria:** all four checks pass and are reported to the developer.

**Git commit message:** N/A (no commit at this stage).

**Explicit out-of-scope:** installing Python/Docker/Git themselves — that is a developer action, not an agent action.

---

## STAGE 1 — Project Skeleton + Configuration

**Objective:** repository, Python environment, directory structure, dependencies, `.env`, and Docker Compose for PostgreSQL are all in place; `git init` done.

**Files/modules:** `docker-compose.yml`, `requirements.txt`, `.env.example`, `.gitignore`, project directory skeleton per the Scope document Section 19 structure (`app/api`, `app/pricing`, `app/forecasting`, `app/data`, `app/logistics`, `app/core`, `data/raw`, `data/demo`, `models`, `tests`, `scripts`, `configs`, `docs`).

**Implementation instructions:**
```
Read AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-STACK.md Section 3 exactly.
Create the directory skeleton and files listed there. Populate requirements.txt
with the pinned versions given in the Stack document Section 2 — do not add
any dependency not on that list (in particular: no `prophet`, no `redis`,
no PostGIS-related packages — these are explicitly DEFERRED, see Scope
document Sections 13/14).
Create docker-compose.yml exactly as specified in the Stack document (plain
postgres:16 image, no PostGIS variant).
Do not write any application logic yet — this stage is scaffolding only.
```

**Tests:** a single trivial test (`test_placeholder.py`) confirming `pytest` itself runs.

**Acceptance criteria:**
- `pip install -r requirements.txt` succeeds inside a fresh venv.
- `docker compose up -d postgres` succeeds and the container is healthy.
- `pytest` runs and passes (even with 1 trivial test).
- Directory structure matches the Scope document's Section 19 layout.

**Git commit message:** `[Stage 1] Project skeleton, dependencies, Docker Compose`

**Explicit out-of-scope:** any FastAPI route, any DB table, any pricing logic.

---

## STAGE 2 — Data Ingestion + Demo Fixtures

**Objective:** DB schema is live; the demo mandi-price fixture is loaded; the `AgmarknetClient` (real + fallback) is implemented per V0.1 §4.2's already-verified field mapping.

**Files/modules:** `app/core/db.py`, `scripts/migrate.py`, `app/data/ingest.py`, `app/data/quality.py`, `configs/crops.yaml`, `configs/mandis.yaml`, `data/demo/mandi_prices.csv`, `data/demo/weather.csv`, `scripts/load_demo_fixture.py`, `scripts/seed_config.py`.

**Implementation instructions:**
```
Implement the trimmed DB schema per Roadmap Day 1 (commodity, mandi,
mandi_price, weather_observation [simplified: mandi_id, obs_date,
rainfall_mm, temp_max_c], demand_signal, prediction_log). Use plain
latitude/longitude NUMERIC columns — do NOT use PostGIS geography types
(Scope document Section 13 — PostGIS is deferred).

Seed configs/crops.yaml with exactly the 5 crops from Scope document
Section 2 (Tomato, Onion, Potato, Rice, Wheat) and configs/mandis.yaml
with 5-10 mandis in one chosen state.

Implement AgmarknetClient reusing the field mapping already verified in
the parent V0.1 spec (state, district, market, commodity, arrival_date,
min_price, max_price, modal_price — arrival_qty is OPTIONAL/may be absent,
per the parent spec's own finding). Do not invent field names not in that
mapping — if a live call is attempted and the field set differs, stop and
report to the developer rather than guessing.

Implement the fallback: if AGMARKNET_API_KEY is unset, or DEMO_MODE=true
in .env, or the live call fails, load data/demo/mandi_prices.csv instead.
Every row loaded this way must be tagged with a source flag distinguishing
it from live data.

Build data/demo/mandi_prices.csv with at least 120 days of history across
all seeded crops and mandis. Prefer real captured Agmarknet data if
available; otherwise generate clearly-synthetic-but-realistic data and
say so explicitly in a code comment and in docs/demo-data-provenance.md.

Implement the data quality pipeline subset from Scope Section 4: missing
modal price -> derive (min+max)/2 and flag; obviously erroneous prices
(<=0 or >20x 30-day median) -> flag, retain, exclude from training,
never delete.
```

**Tests:**
- Schema migration applies cleanly to a fresh DB.
- Demo fixture loads without errors and produces the expected row count.
- A record with missing modal price but present min/max is correctly derived and flagged.
- A record with an obviously erroneous price is flagged and retained (not deleted).
- Fallback path triggers correctly when `DEMO_MODE=true`.

**Acceptance criteria:** `python scripts/load_demo_fixture.py` populates the DB; a query against `mandi_price` returns real rows for every seeded crop/mandi pair.

**Git commit message:** `[Stage 2] DB schema, config seeding, ingestion + demo fixture fallback`

**Explicit out-of-scope:** scheduled/cron ingestion, historical backfill chunking, `unmapped_mandis`/`unmapped_commodities` review tables (all DEFER TO V0.1 per Scope §4).

---

## STAGE 3 — Feature Engineering + Baseline

**Objective:** the reduced feature set (Scope §6) and the deterministic baseline formula (V0.1 §8, unchanged) are implemented and unit-tested.

**Files/modules:** `app/features/engineering.py`, `app/features/demand.py`, `app/forecasting/baseline.py`.

**Implementation instructions:**
```
Implement lag_1, rolling_mean_7, price_momentum (7d), volatility_30d as
pure functions over a price series, each threaded through an as_of_date
parameter so no feature can see data from after the prediction timestamp
(point-in-time discipline — do not skip this, it's cheap and it's a core
credibility claim per V0.1 section 48 Q16).

Implement the Demand Index exactly as corrected by the parent audit:
norm(x) = 0 when max == min (including the all-zero case) — this MUST
NOT divide by zero under any input. Write a test that specifically
exercises the all-zero cold-start case before considering this done.

Implement the baseline formula exactly as V0.1 section 8 specifies:
Baseline(t) = 0.4*ModalPrice(t-1) + 0.3*WeightedMovingAvg(7d)
            + 0.2*RegionalMedian(state,commodity,t-1) + 0.1*SeasonalIndex
using exponential weights (0.9^i) for the weighted moving average.
This is a pure, deterministic function - it must never call the ML
model or any network/DB call beyond reading already-fetched price rows.
```

**Tests:**
- Baseline formula matches a hand-calculated fixture value exactly.
- Weighted moving average matches a hand-calculated fixture.
- Demand Index cold-start (`max == min`) returns `0`, no exception.
- A feature computed with `as_of_date = t` does not use any row with `price_date > t` (leakage spot check).

**Acceptance criteria:** all feature functions and the baseline are callable independently, with passing unit tests, using only data already ingested by Stage 2.

**Git commit message:** `[Stage 3] Feature engineering + deterministic baseline model`

**Explicit out-of-scope:** the ML model itself (Stage 4), weather anomaly/climatology features (DEFER TO V0.1 per Scope §6).

---

## STAGE 4 — ML Forecasting

**Objective:** the sklearn `HistGradientBoostingRegressor` model trains against the demo dataset with a walk-forward validation split, and its forecast can be retrieved for any seeded (crop, mandi) pair, with a fallback to baseline when data is insufficient.

**Files/modules:** `app/forecasting/sklearn_model.py`, `scripts/train.py`, `models/` (artifact output directory).

**Implementation instructions:**
```
Implement a single walk-forward train/validation split (never shuffled -
use a small TemporalSplitter utility function so this can never be
accidentally violated by a future edit). Train HistGradientBoostingRegressor
using the Stage 3 features as inputs.

Per Scope document Section 5: if a pooled (all-crop, all-mandi) model is
faster to get working than per-pair models within the day's time budget,
that is an acceptable Stage 4 shortcut - use crop and mandi as categorical
features in that case. Per-pair models are the ideal but not required for
MVP.

Compute MAE against a naive lag-1 baseline on the held-out validation
window. If a given (crop, mandi) pair has fewer observations than a
configurable minimum (recommend 60, consistent with the parent spec's
own >=60-in-90-days rule), skip ML training for that pair entirely and
mark it baseline-only - do not train on an insufficient window and
report a misleadingly confident metric.

Save the trained model artifact under models/, plus a simple JSON file
recording MAE-vs-baseline per (crop, mandi) pair actually trained.
```

**Tests:**
- Training runs to completion on the demo dataset without error.
- The temporal splitter never produces overlapping train/validation date ranges (assert no shuffle occurred).
- A (crop, mandi) pair with insufficient data is correctly routed to baseline-only, not silently trained anyway.
- Model reproducibility: same seed + same data → MAE within a small tolerance across two runs.

**Acceptance criteria:** `python scripts/train.py --all-crops` completes; for at least one (crop, mandi) pair, the trained model's forecast is retrievable and its MAE is reported against the naive baseline.

**Git commit message:** `[Stage 4] sklearn forecasting model + walk-forward validation`

**Explicit out-of-scope:** Prophet, per-pair model selection logic with acceptance-threshold gating across dozens of pairs, model versioning/rollback tooling (all DEFER TO V0.1 per Scope §5).

---

## STAGE 5 — Demand + Weather Signal Wiring

**Objective:** the Demand Index (Stage 3) and weather features are wired into the forecasting model's feature set as model inputs — not as a separate additive price adjustment.

**Files/modules:** `app/features/demand.py` (extend), `app/features/weather.py` (new), integration point in `app/forecasting/sklearn_model.py`.

**Implementation instructions:**
```
CRITICAL: read Scope document Section 7 and the parent audit's Finding
F1 before writing any code in this stage. Weather and demand signals
must enter the model exactly once, as regressor/feature inputs to the
sklearn model already built in Stage 4. They must NEVER also be added
as a second, independent rupee adjustment later in the pricing formula
(that happens in Stage 6) - that would reintroduce the exact
double-counting defect the parent audit found and fixed (Finding F1,
CRITICAL severity). If you find yourself about to write a line like
`price += demand_adjustment` anywhere outside the model's own feature
set, stop and flag this to the developer before proceeding.

Implement two weather features: rainfall_mm and temp_max_c, sourced
from data/demo/weather.csv (a small labeled fixture is sufficient if
no live weather API is wired up - mark it as DEMO DATA same as the
price fixture).

Re-train the Stage 4 model with these features included and confirm
the MAE does not get worse (if it does, investigate before proceeding -
a well-implemented added feature should not hurt validation MAE by more
than noise-level amounts).
```

**Tests:**
- The all-zero demand cold-start case (Stage 3's test) still passes after wiring into the model — the model's feature-preparation step must handle a `None`/excluded demand feature without crashing, per the audit's guidance to exclude rather than zero-force when there's truly no history.
- A regression test asserting that weather/demand features appear exactly once in the model's feature vector, with no corresponding second adjustment term anywhere in `app/pricing/` (this test intentionally polices Stage 6's future code too — write it now).

**Acceptance criteria:** re-trained model includes weather/demand features; MAE reported is comparable to or better than Stage 4's baseline-features-only run.

**Git commit message:** `[Stage 5] Wire demand + weather as model regressors (no double-counting, per audit F1)`

**Explicit out-of-scope:** rainfall/temp anomaly-vs-climatology features, extreme-weather binary flags (DEFER TO V0.1 per Scope §6).

---

## STAGE 6 — Price Discovery + Reliability

**Objective:** the corrected single-term price discovery formula, farmer floor check, and 3-component reliability score are implemented and orchestrated into one callable function.

**Files/modules:** `app/pricing/discovery.py`, `app/pricing/farmer_floor.py`, `app/pricing/reliability.py`, `app/pricing/explain.py`, `app/pricing/orchestrate.py`.

**Implementation instructions:**
```
Implement exactly this formula (Scope document Section 7 — this is the
audit-corrected V0.1 formula, reused verbatim, not re-derived):

  FairPrice = Baseline + w_forecast * (Forecast - Baseline)
  Lower = FairPrice * (1 - spread)
  Upper = FairPrice * (1 + spread)

where spread = clamp(0.03 + 0.5*volatility_30d, 0.02, 0.15) — the MVP's
simplified single-variable spread function (Scope document Section 7).
w_forecast defaults to 0.5, config-driven.

Implement the farmer floor: FLOOR = 0.85 * Baseline. If FairPrice.Lower
< FLOOR, return status "REVIEW REQUIRED" with a logged reason string —
do not silently allow it through.

Implement the Reliability Score exactly as the 3-component MVP formula
in Scope document Section 10:
  Reliability = 100 * (0.35*DataFreshness + 0.30*HistoricalVolume + 0.35*ValidationQuality)
Each sub-component normalized 0-1. Do not add a ModelAgreement term —
there is only one ML model in this MVP, so that term has nothing to
compare against (this is a deliberate omission, not a shortcut needing
a workaround default).

Implement a plain-language explanation generator producing one sentence
per signal (market, forecast, demand, weather, logistics, reliability),
avoiding causal language ("X caused the price to rise") in favor of
contributory language ("X was among the model's inputs").

Orchestrate all of the above plus Stage 7's logistics output (once
available) into a single predict_price(commodity, quantity_kg,
farmer_location, buyer_location) function returning one result object.
```

**Tests:**
- Hand-calculated fixture (build one now, from a real run against the demo data) matches the code's output exactly — this becomes the MVP's permanent regression fixture, same discipline as the parent spec's `PRICE-E2E-001`.
- Farmer floor triggers correctly on a forced low-price scenario.
- Farmer floor does not falsely trigger on a normal scenario.
- Reliability score always within [0, 100] across a range of synthetic sub-component inputs.
- `Lower < FairPrice < Upper` always holds.

**Acceptance criteria:** `predict_price(...)` returns a complete, internally consistent result for at least the Tomato demo scenario; the hand-verified fixture matches exactly (do not proceed to Stage 8 dashboard work until this reconciles).

**Git commit message:** `[Stage 6] Price discovery, farmer floor, reliability score, explanation text`

**Explicit out-of-scope:** buyer affordability adjustment, full JSON explanation schema, STRESSED-volatility confidence cap (all DEFER TO V0.1 per Scope §7/§10/§11).

---

## STAGE 7 — Logistics

**Objective:** a simple deterministic logistics cost calculator, feeding into Stage 6's orchestration function.

**Files/modules:** `app/logistics/cost.py`, `app/core/geo.py` (haversine utility).

**Implementation instructions:**
```
Implement a haversine distance function (plain Python, no PostGIS -
Scope document Section 13). Implement:

  CostPerShipment = distance_km * per_km_rate + handling_cost
  CostPerKg = CostPerShipment / quantity_kg

with per_km_rate and handling_cost as config-driven values (configs/
logistics.yaml), explicitly labeled illustrative/prototype assumptions,
matching V0.1's own "ASSUMPTION, config-driven" treatment of these rates.
Single vehicle class only - no vehicle-class-selection-by-capacity logic.

Wire this into Stage 6's orchestration function so predict_price(...)
returns a full breakdown: FarmerPayout, LogisticsCostPerKg, PlatformFeePerKg,
BuyerPrice = FarmerPayout + LogisticsCostPerKg + PlatformFeePerKg.
```

**Tests:**
- Logistics cost matches a hand-calculated fixture exactly, given known distance/quantity/rate inputs.
- `BuyerPrice` equals the exact sum of its three components, no rounding drift beyond 2 decimals.
- Haversine distance matches a known reference distance (e.g., two well-known coordinate pairs) within a small tolerance.

**Acceptance criteria:** the full `predict_price(...)` result now includes a complete, internally consistent final breakdown matching V0.1 §21's format.

**Git commit message:** `[Stage 7] Logistics cost calculator + final price breakdown`

**Explicit out-of-scope:** pooling, vehicle-class selection, spoilage buffer cost, real road routing (all DEFER TO V0.1 per Scope §9).

---

## STAGE 8 — FastAPI Integration

**Objective:** `predict_price(...)` and basic market-data lookups are exposed via FastAPI endpoints.

**Files/modules:** `app/api/predict.py`, `app/api/market.py`, `app/main.py`.

**Implementation instructions:**
```
Implement:
  POST /predict-price  {commodity, quantityKg, farmerLocation, buyerLocation}
    -> full predict_price(...) result as JSON
  GET /market-price?commodity=&mandi=
    -> recent mandi_price rows for that pair

Use Pydantic models for request/response validation. Reject invalid
inputs (unknown crop, non-positive quantity, out-of-India-bounding-box
coordinates) with a 4xx error and a clear message, before they reach
predict_price(...) at all.

Do NOT add authentication, rate limiting, or a Node.js proxy layer -
this MVP's dashboard calls FastAPI directly (Scope document Section 12,
explicitly flagged MVP-only deviation from the parent V0.1 spec).
```

**Tests:**
- `POST /predict-price` with valid input returns 200 and the full result schema.
- Unknown crop returns 400 with a clear message.
- Zero or negative quantity returns 400/422.
- Out-of-range coordinates return 400/422.
- `GET /market-price` returns recent rows for a seeded pair, 404 for an unseeded one.

**Acceptance criteria:** all Stage 8 endpoints are reachable via `curl`/Swagger UI (`/docs`) and return correct, validated responses.

**Git commit message:** `[Stage 8] FastAPI endpoints for prediction and market data`

**Explicit out-of-scope:** `/logistics/estimate`, `/price-explanation`, `/model/status` as separate endpoints — fine to fold their data into `/predict-price`'s response for MVP rather than building 4 more endpoints (DEFER the full V0.1 §25 endpoint set).

---

## STAGE 9 — Dashboard

**Objective:** the Streamlit professor-facing dashboard, calling Stage 8's FastAPI endpoints, with the 3 required charts and explanation panel.

**Files/modules:** `dashboard/app.py`, `dashboard/charts.py`, `dashboard/components.py`.

**Implementation instructions:**
```
Build the panels exactly as listed in Scope document Section 15/16:
input panel, market panel, AI panel, demand/weather panel, logistics
panel, final breakdown, explanation panel, plus 3 charts (historical
price trend, forecast-vs-actual, price decomposition bar).

Call FastAPI's /predict-price and /market-price directly via `requests`
(no Node.js layer, per Stage 8's decision).

Show a visible "DEMO DATA" badge whenever the result's dataSource
indicates fixture-derived data (Scope document Section 4).

Handle failure gracefully: if FastAPI is unreachable, show a clear
"backend unavailable" message rather than a stack trace or a frozen
spinner. If an invalid input is selected, show a clear message rather
than crashing the page.
```

**Tests:**
- A Streamlit smoke test (or manual checklist, if automated UI testing is out of scope for the time budget) confirming the Section 1 demo scenario renders all panels correctly.
- Backend-down scenario shows the graceful error state, not a crash.

**Acceptance criteria:** a person unfamiliar with the code can run the full demo scenario using only the dashboard, no terminal.

**Git commit message:** `[Stage 9] Streamlit dashboard with charts and explanation panel`

**Explicit out-of-scope:** map view, React, any Node.js integration.

---

## STAGE 10 — Testing + Hardening

**Objective:** full test suite (15–25 tests per the Roadmap checklist), failure-mode simulation, README, and rehearsed demo.

**Files/modules:** `tests/` (all remaining test files), `README.md`, `docs/architecture-diagram.png` or `.md`, `docs/demo-data-provenance.md`.

**Implementation instructions:**
```
Implement the remaining tests from the Roadmap document's Testing
Checklist not already covered by earlier stages. Run the full suite;
report pass/fail for every test; do not skip or xfail a failing test -
report it and propose a fix instead.

Simulate live-API failure (invalid URL or unset API key) and confirm
the system falls through to the demo fixture cleanly, with the badge
visible in the dashboard.

Simulate model-artifact-unavailable (rename/move the models/ directory
temporarily) and confirm baseline-only mode still produces a full,
correctly-labeled result, not an error.

Write README.md covering: setup commands (reuse the Stack document's
exact commands), how to run ingestion/training/dashboard, and a short
architecture summary naming what's deferred to V0.1 and why (reuse
Scope document Section 17's table).

Do not modify app/pricing/, app/forecasting/, or app/logistics/ logic
during this stage unless a test failure specifically requires a bug fix
in that logic - this stage is about verification and packaging, not
new feature work.
```

**Tests:** the full 15–25 test suite from the Roadmap document.

**Acceptance criteria:** the Section 1 demo scenario runs 5 consecutive times without a crash or inconsistent result; both failure-mode simulations (API down, model unavailable) degrade gracefully; README is complete enough for someone else to set up the project from scratch using only it.

**Git commit message:** `[Stage 10] Test suite, failure-mode hardening, README, demo rehearsal artifacts`

**Explicit out-of-scope:** any new feature, any scope item from the Scope document's "Explicitly Removed / Deferred" table (Section 17).

---

## Post-Stage-10: Presentation Rehearsal (not a coding stage)

Not an agent task — a developer task. Run the Roadmap document's Professor Presentation Sequence at least twice, timing each segment, using the frozen demo dataset and the Section 1 scenario. Confirm the "kill the live API mid-demo" fallback moment works reliably before relying on it live.
