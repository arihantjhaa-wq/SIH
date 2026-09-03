# AGRI-DIRECT PRICING ENGINE — INTERNAL HACKATHON MVP
## Implementation Roadmap (3–5 Days)

Companion to `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-SCOPE.md` (scope authority) and `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-STACK.md` (tech decisions). Stage prompts for each day live in `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-AGENT-PROMPTS.md`.

This roadmap assumes: developer starting from zero, Windows machine, Antigravity IDE with AI agentic coding, no prior project code, Docker available.

---

## Day-by-Day Overview

| Day | Focus | Exit criterion |
|---|---|---|
| 1 | Foundation | System starts successfully |
| 2 | Data + baseline + ML | A crop/mandi combination produces a forecast |
| 3 | Pricing engine | One complete transaction can be calculated |
| 4 | Dashboard + integration | A professor can use the system without a terminal |
| 5 | Hardening + demo | The full demo runs repeatedly without breaking |

If only 3–4 days are available: Days 1–3 are non-negotiable (they produce the working engine). Day 4 (dashboard) can be compressed to a bare Streamlit page with no chart polish. Day 5 (hardening) is the first thing to cut, but Section "Minimum Viable Day 5" below gives the smallest defensible version of it — do not skip fallback-mode testing and the rehearsed demo script entirely, since those are what prevent a live failure in front of professors.

---

## DAY 1 — FOUNDATION

**Objective:** repository, environment, project structure, dependencies, database, demo dataset skeleton, config, and a bare `/health` endpoint are all live.

### Tasks
- Initialize git repository; first commit is the project skeleton (Section 19 of the Scope doc's directory structure).
- Create Python virtual environment; install pinned dependencies (`requirements.txt` — see Stack doc).
- Stand up PostgreSQL (Docker Compose recommended — one `docker-compose.yml` with a `postgres` service; no PostGIS extension needed per Scope §13).
- Write the DB schema migration: `commodity`, `mandi`, `mandi_price`, `demand_signal`, `prediction_log` tables — a trimmed version of V0.1 §3's DDL (drop `geography` columns, use plain `latitude`/`longitude NUMERIC`; drop `weather_observation`'s `is_forecast`/`source` columns if not needed yet, keep it simple: `mandi_id, obs_date, rainfall_mm, temp_max_c`).
- Seed `configs/crops.yaml` and `configs/mandis.yaml` with the 5 crops and 5–10 mandis (Scope §2/§3).
- Build a minimal `data/demo/mandi_prices.csv` fixture — even a small placeholder is fine on Day 1; it gets filled out properly on Day 2.
- Scaffold FastAPI app with a single `GET /health` endpoint returning `{status, dbOk}`.

### Files/modules
`docker-compose.yml`, `app/core/config.py`, `app/core/db.py`, `app/api/health.py`, `scripts/migrate.py` or Alembic, `configs/crops.yaml`, `configs/mandis.yaml`, `.env.example`, `requirements.txt`.

### Acceptance criteria
- `pytest` runs (even with 0 or 1 trivial test).
- `uvicorn app.main:app` starts locally without error.
- `GET /health` returns 200 with `dbOk: true` against the local Postgres container.
- `git log` shows an initial commit.

### Dependencies
None — this is the first day.

---

## DAY 2 — DATA + BASELINE + ML

**Objective:** market data ingestion (real + fallback), cleaning, feature engineering, baseline formula, and the chosen ML model (sklearn `HistGradientBoostingRegressor`, per Stack doc) all work end-to-end against the demo dataset, producing a validated forecast for at least one (crop, mandi) pair.

### Tasks
- Build `data/demo/mandi_prices.csv` out properly: multi-month history (recommend ≥120 days) across all 5 crops and all seeded mandis, either drawn from a real captured Agmarknet sample (preferred, matches V0.1 §37's "real historical data captured in advance" principle) or clearly-labeled synthetic data if time is short.
- Implement `AgmarknetClient` (reuse V0.1 §4.2's verified field mapping directly — no re-derivation needed) with a simple try/fallback: if the live API call fails or is not configured, load the demo CSV instead. Log which path was used.
- Implement the data quality pipeline subset (Scope §4): missing modal price → derive from min/max; obvious price errors → flag, retain, exclude from training (same "never delete" principle as V0.1 §5, just without the full quarantine-table tooling).
- Implement feature engineering (Scope §6): `lag_1`, `rolling_mean_7`, `price_momentum`, `volatility_30d`; rainfall/temp features (from a small demo weather fixture if no live weather integration); Demand Index with the audit's cold-start fix (`norm(x) = 0` when `max == min`).
- Implement the baseline formula (V0.1 §8, unchanged) as a pure function with unit tests using known fixed inputs.
- Implement the sklearn `HistGradientBoostingRegressor` model: single walk-forward train/validation split (never shuffled), trained per (crop, mandi) or, if time is short, a single pooled model with crop/mandi as categorical features — pooled model is an acceptable Day 2 fallback if per-pair training doesn't fit the day.
- Save the trained model artifact to `models/` and record basic metrics (MAE vs. naive baseline) in a simple JSON/DB row — no full `ModelVersion` versioning table required yet (that's V0.1 machinery); a single "latest model" file is enough for MVP.

### Files/modules
`app/data/ingest.py`, `app/data/quality.py`, `app/features/engineering.py`, `app/features/demand.py`, `app/forecasting/baseline.py`, `app/forecasting/sklearn_model.py`, `scripts/train.py`, `data/demo/mandi_prices.csv`, `data/demo/weather.csv`.

### Acceptance criteria
- Baseline formula unit test passes against a hand-calculated fixture value.
- Demand Index cold-start test passes (`max == min` → `0`, no exception).
- `python scripts/train.py --crop tomato --mandi <seeded-mandi-id>` runs to completion and prints an MAE that beats naive-lag-1 (or, if it doesn't beat it for every crop, the system correctly falls back to baseline-only for that pair — this is expected/acceptable behavior, not a failure, per V0.1 §12's own "baseline wins" case).
- A forecast value can be retrieved programmatically (a plain Python function call is sufficient; the API endpoint for it comes on Day 3/4).

### Dependencies
Day 1's DB schema and config must exist.

---

## DAY 3 — PRICING ENGINE

**Objective:** the full pricing calculation — demand, weather signal, price discovery, farmer protection, reliability score, explanation text, logistics, and final price breakdown — runs as one function call producing a complete, internally consistent result for a single (crop, quantity, farmer location, buyer location) input.

### Tasks
- Wire the Demand Index and weather features (already built Day 2) into the model's feature set — **not** as a separate additive term (Scope §7 — this is the exact defect the parent audit found and fixed; do not reintroduce it here).
- Implement price discovery: `FairPrice = Baseline + w_forecast × (Forecast − Baseline)`, `Lower/Upper = FairPrice × (1 ∓ spread)`, with the simplified single-variable `spread(volatility_30d)`.
- Implement the farmer floor check (`FLOOR = 0.85 × Baseline`; `REVIEW REQUIRED` if `Lower < FLOOR`).
- Implement the Reliability Score (3-component version per Scope §10).
- Implement the logistics calculator (haversine distance × per-km rate + handling cost, single vehicle class, Scope §9).
- Implement the final breakdown (`BuyerPrice = FarmerPayout + LogisticsCost + PlatformFee`).
- Implement the explanation text generator — plain-language sentences per signal (market/forecast/demand/weather/logistics/reliability), no causal language.
- Assemble all of the above into one orchestration function, e.g. `predict_price(commodity, quantity_kg, farmer_location, buyer_location) -> PricingResult`.
- Hand-verify one full worked example end-to-end (a Tomato scenario) and write it down — this becomes the Day 5 regression-test fixture, mirroring V0.1 §41.1's `PRICE-E2E-001` approach at MVP scale.

### Files/modules
`app/pricing/discovery.py`, `app/pricing/farmer_floor.py`, `app/pricing/reliability.py`, `app/pricing/explain.py`, `app/logistics/cost.py`, `app/pricing/orchestrate.py`.

### Acceptance criteria
- `predict_price(...)` returns a single object with all fields from the Section 1 demo objective (Scope doc) populated and internally consistent (`Lower < FairPrice < Upper`; `BuyerPrice = FarmerPayout + Logistics + PlatformFee` exactly, no rounding drift beyond 2 decimals).
- A forced low-price scenario triggers `REVIEW REQUIRED` correctly; a normal scenario does not falsely trigger it.
- The hand-verified worked example matches the code's output exactly (this is the Day 3 exit gate — do not proceed to Day 4 until this reconciles, exactly as the parent audit's F2 finding warns against shipping an unverified worked example).

### Dependencies
Day 2's baseline, model, and feature functions.

---

## DAY 4 — DASHBOARD + INTEGRATION

**Objective:** a professor can run the entire demo through a Streamlit page, without touching a terminal, with charts and an explanation panel, calling the FastAPI backend built alongside it.

### Tasks
- Build `POST /predict-price` and `GET /market-price` FastAPI endpoints wrapping Day 3's `predict_price` function and Day 2's raw price lookups.
- Build the Streamlit dashboard (Scope §15) with: input panel (crop dropdown, quantity, farmer/buyer location — dropdowns of seeded mandis/locations are fine, no need for a map picker), market panel, AI panel, demand/weather panel, logistics panel, final breakdown, explanation panel.
- Wire the dashboard to call FastAPI directly (Scope §12's flagged MVP-only deviation — no Node.js layer).
- Build the 3 required charts (Scope §16): historical price trend, forecast-vs-actual, price decomposition bar.
- Add basic error handling: invalid crop/location selection shows a friendly message, not a stack trace; if FastAPI is unreachable, the dashboard shows a clear "backend unavailable" state rather than hanging or crashing.
- Add the **DEMO DATA** badge wherever `dataSource == "demo_fixture"` is returned.

### Files/modules
`app/api/predict.py`, `app/api/market.py`, `dashboard/app.py` (Streamlit entry point), `dashboard/charts.py`, `dashboard/components.py`.

### Acceptance criteria
- Launching `streamlit run dashboard/app.py` and entering the Section 1 demo scenario produces the full Section 1 output on screen, with charts rendering.
- Selecting an unsupported input (e.g., a crop not in config) shows a clear message, not a crash.
- Killing the FastAPI process and refreshing the dashboard shows a graceful "backend unavailable" message, not a frozen UI.
- A person unfamiliar with the code can operate the full flow using only the dashboard.

### Dependencies
Day 3's pricing orchestration function.

---

## DAY 5 — HARDENING + DEMO

**Objective:** the system survives repeated runs, common edge cases, and a simulated live-API failure, and the demo script is rehearsed and screenshotted.

### Tasks
- Write the test suite (15–25 tests; see the checklist below — same categories as required by the MVP brief).
- Run the full suite; fix failures; do not skip or xfail a failing test (same discipline as V0.1 §43).
- Simulate Agmarknet API failure (unplug network or point the client at an invalid URL) and confirm the system falls through to the demo fixture cleanly, with the DEMO DATA badge appearing.
- Simulate "model unavailable" (rename/move the model artifact) and confirm baseline-only mode still produces a full, correctly-labeled result rather than an error.
- Polish the dashboard (labels, number formatting ₹ with 2 decimals, consistent badge styling).
- Freeze `data/demo/mandi_prices.csv` as the official demo dataset; re-run the Section 1 scenario against it one final time and screenshot the result.
- Write `README.md`: setup commands (Section "Local Development Environment" in the Stack doc), how to run ingestion/training/dashboard, and a one-paragraph architecture summary.
- Draw a simple architecture diagram (can be a basic box-and-arrow image, does not need to match V0.1's Mermaid diagram exactly, but should visually communicate: Streamlit → FastAPI → Pricing Engine → PostgreSQL / demo fixture).
- Rehearse the 5–7 minute presentation sequence at least twice, timing each section (see below).

### Minimum Viable Day 5 (if only 3–4 total days are available)
If Day 5 must be compressed: keep (a) the API-failure and model-unavailable fallback tests — these are what prevent an on-stage crash — and (b) one full rehearsal of the demo scenario. Cut: the full 15–25 test suite (keep the 6–8 most important, see checklist), the architecture diagram, and dashboard polish.

### Acceptance criteria
- The Section 1 demo scenario can be run 5 times in a row without a crash or an inconsistent result.
- Killing the (simulated) live data source mid-session does not break the dashboard.
- The presenter has rehearsed the demo at least twice within the target time window.

---

## Testing Checklist (15–25 tests, MVP-scoped subset of V0.1 §31)

| # | Category | Scenario |
|---|---|---|
| 1 | Happy path | Valid crop/mandi/qty/locations → full result, `range.min < range.max` |
| 2 | Unknown crop | Rejected with a clear message |
| 3 | Missing mandi data | Falls back to demo fixture or nearby mandi, does not crash |
| 4 | Missing weather data | Prediction still proceeds, weather term simply absent from explanation |
| 5 | Missing demand data (cold start) | `norm(x) = 0`, no divide-by-zero, no exception |
| 6 | Extreme/outlier price in input data | Flagged, retained, excluded from training — not silently dropped |
| 7 | Zero quantity | Rejected with a validation error |
| 8 | Negative quantity | Rejected with a validation error |
| 9 | Very large quantity (e.g. 1,000,000 kg) | Handled without overflow/crash; sane output or explicit "out of realistic range" message |
| 10 | Invalid location (out of India bounding box or malformed) | Rejected with a validation error |
| 11 | Live API failure | Falls through to `data/demo/mandi_prices.csv`, DEMO DATA badge shown |
| 12 | Model artifact unavailable | Falls back to baseline-only, response clearly labeled |
| 13 | Stale data (price older than N days) | Reliability score reduced, but system still returns a result, not an error |
| 14 | Farmer protection trigger | Forced low-price scenario returns `REVIEW REQUIRED` |
| 15 | Farmer protection not falsely triggered | Normal scenario does not trigger it |
| 16 | Baseline formula correctness | Matches hand-calculated fixture exactly |
| 17 | Logistics calculation correctness | Matches hand-calculated fixture exactly |
| 18 | Final price breakdown correctness | `BuyerPrice = FarmerPayout + Logistics + PlatformFee` exactly |
| 19 | Reliability score bounds | Always within [0, 100] |
| 20 | Demand Index bounds | Always within [0, 100] |
| 21 | End-to-end worked example (regression fixture from Day 3) | Every intermediate value matches the frozen fixture |
| 22 | Dashboard graceful backend-down state | No frozen UI, clear message |
| 23 | Repeat-run consistency | Same inputs → same outputs across 3 consecutive runs |
| 24 | Config-driven crop addition (optional stretch) | Adding a 6th crop to `configs/crops.yaml` does not require a code change |
| 25 | No-leakage spot check | A feature computed `as_of_date = t` does not use any `price_date > t` row |

If time only allows a subset, prioritize #1, #6, #11, #12, #14, #18, #21 — these are the tests that most directly prevent a visible on-stage failure.

---

## Professor Presentation Sequence (5–7 minutes)

| Time | Segment |
|---|---|
| 0:00–0:45 | Problem statement (SIH26033 — intermediaries reduce farmer earnings, raise consumer prices) |
| 0:45–1:30 | The traditional intermediary chain, briefly — what a farmer typically loses today |
| 1:30–2:30 | AgriDirect architecture overview — one diagram, name each component, note this MVP is a scoped-down slice of a larger frozen V0.1 specification |
| 2:30–4:30 | Live prototype demonstration — run the Section 1 scenario live, walk through each panel as it appears |
| 4:30–5:30 | Price transparency — open the explanation panel, show the final breakdown, emphasize nothing is a black box |
| 5:30–6:30 | Technical architecture + ML — what model, why, what data, how validated, what happens on failure (trigger one live fallback if time allows — killing the API connection is the strongest 15-second demo moment available) |
| 6:30–7:00 | Future scalability — this MVP's exact upgrade path to the frozen V0.1 spec (Node.js, PostGIS, Redis, Prophet, pooling — name what's deferred and why, not hidden) |

---

## Expected Professor Questions & Answers

1. **Where does the mandi data come from?** data.gov.in's AGMARKNET-mirrored resource, verified field-by-field; falls back to a real historical snapshot (not fabricated numbers) if the live API is unavailable during demo.
2. **Why use ML at all here?** A deterministic baseline already exists and is always available; the ML model's job is only to capture nonlinear multi-signal interactions (weather × demand × recent trend) that a fixed formula can't — and it's only trusted where it demonstrably beats the baseline.
3. **Why scikit-learn and not Prophet/deep learning?** Prophet is deferred purely for install-risk reasons in a 3–5 day window, not a capability judgment — it's the planned V0.1 second model. Deep learning is excluded on data-volume and explainability grounds, same reasoning either version of this project uses.
4. **How accurate is it?** Report the actual MAE vs. the naive-lag-1 baseline from Day 2's training run — never promise a MAPE figure you haven't measured.
5. **What happens when data is missing?** Fallback hierarchy engages (nearby mandi → demo fixture), never silently substituted — the reliability score visibly drops and the source is labeled.
6. **What if the market suddenly crashes/spikes?** `volatility_30d` widens the price range automatically; the number isn't hidden, the uncertainty is shown.
7. **How does this benefit farmers?** The price floor is a hard constraint (`REVIEW REQUIRED`, not silently allowed) — show it triggering live if possible.
8. **How is demand calculated?** Platform's own order activity only, explicitly not nationwide consumer demand — state this proactively, don't wait to be asked.
9. **How is logistics calculated?** Explicit distance × rate + handling formula, shown in the breakdown panel, config-driven and labeled illustrative.
10. **Is this scalable?** Every crop/mandi is a config row, not code — show the config file live if asked.
11. **What is actually "AI" here?** The forecasting model (learned from historical price/weather/demand patterns); the rest (floor, logistics, breakdown) is deliberately transparent arithmetic, by design, so the AI component doesn't have to be trusted blindly.
12. **What is your innovation?** Not "using AI on mandi data" — that's been done. The differentiator is the system design: explainability, fallback discipline, farmer-floor-as-hard-constraint, and a transaction-completing price+logistics answer rather than a historical-lookup portal.
13. **What prevents manipulation?** All computation is server-side; no client-supplied price is ever trusted as input.
14. **What happens if the prediction is wrong?** Bounded by validation before it's ever served; baseline is always the floor of trust; nothing is deployed without beating the naive baseline first.
15. **How is this different from existing mandi price portals?** Portals show historical prices only; this produces a forward-looking, logistics-aware, transaction-ready price with an explicit uncertainty range.

---

## Explicitly Not Built in This MVP

Restated from the Scope document for presentation use — say this proactively, don't wait to be asked:

Node.js gateway/auth, PostGIS, Redis, Prophet, dual-model agreement scoring, logistics pooling and vehicle-class selection, spoilage modeling, the full explanation JSON API contract, scheduled/automated ingestion, buyer affordability adjustment, the "Where did my ₹100 go?" comparison visual (needs cited sourcing first), and — same as the parent V0.1 spec — deep learning, Kafka, Kubernetes, MLflow, CI pipelines, route optimization, and production payments/auth.
