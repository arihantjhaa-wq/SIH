# AGRI-DIRECT PRICING ENGINE — INTERNAL HACKATHON MVP
## Scope Definition

**Parent document (frozen, unmodified):** `AGRI-DIRECT-PRICING-ENGINE-V0.1-SPEC-FINAL.md`
**Parent audit (frozen, unmodified):** `AgriDirect_Pricing_Engine_V0.1_AUDIT.md`
**This document:** a strictly reduced derivative for a 3–5 day internal hackathon prototype, demoed to college professors, built by a developer starting from zero using Antigravity IDE + AI agentic coding.

**Relationship to the parent spec:** every decision below is a *subset* of V0.1, never a contradiction of it. Where this MVP simplifies something (e.g., dropping Node.js, dropping PostGIS), the underlying V0.1 formula/architecture is preserved so the MVP can be grown into V0.1 without a rewrite — only additive work, no throwaway work. Any place this MVP diverges from a V0.1 rule (e.g., frontend calling the pricing engine directly instead of through Node.js) is called out explicitly as an **MVP-ONLY DEVIATION**, not a silent contradiction.

Legend: **MVP REQUIRED** · **MVP OPTIONAL** · **DEFER TO V0.1** · **REMOVE (not even in V0.1 near-term)**

---

## 1. Demo Objective

A professor enters:
```
Crop: Tomato
Quantity: 500 kg
Farmer Location: Location A
Buyer Location: Location B
```
and sees, within seconds, a single-screen result:
```
Current Mandi Price        ₹22.00/kg
Predicted Market Price     ₹24.00/kg
Fair Farmer Price Range    ₹23.00–25.00/kg
Demand                     HIGH (platform-only signal)
Weather/Supply Signal      MODERATE RISK
Estimated Logistics        ₹2.40/kg
Platform Fee               ₹0.25/kg
Estimated Buyer Price      ₹26.00–28.00/kg
Prediction Reliability     78/100
```
Every number is traceable to a plain-language explanation panel. Nothing displayed is unexplainable, and nothing synthetic is shown without a visible **DEMO DATA** label.

**Definition of done for the MVP:** this flow runs start-to-finish, repeatedly, without a terminal, entirely offline if needed, and every number in the output can be defended verbally against the questions in Section 24 of the roadmap/prompts documents.

---

## 2. Crops — MVP REQUIRED

Exactly **5 crops**, config-driven (not hardcoded), chosen to mirror the parent spec's `fruit_veg`/`root`/`grain` category split so the demand/weather/spoilage logic has at least one example of each perishability behavior:

| Crop | Category | Why included |
|---|---|---|
| Tomato | fruit_veg | Primary demo crop — high volatility, good story for price ranges and weather sensitivity |
| Onion | fruit_veg | Second highly-volatile crop, reinforces "not a fluke" when comparing two crops live |
| Potato | root | Lower volatility contrast crop, useful for showing MAE differences across crop types |
| Rice | grain | Low-volatility grain, demonstrates the baseline/model behaves sensibly across very different price dynamics |
| Wheat | grain | Second grain, cheap to add once Rice's pipeline works — proves config-driven scaling with near-zero marginal effort |

All 5 crops share one `Commodity` config schema (per V0.1 §2/§3) — adding a 6th crop later is a config-file change, not a code change. This is a live-demo talking point (V0.1 §48 Q11).

---

## 3. Geography — MVP REQUIRED

**One state, 5–10 mandis** — same scope as V0.1, unchanged. No reduction needed here; V0.1 was already hackathon-appropriately scoped.

Rationale to give professors directly: a full India-wide dataset would not improve demo credibility (judges/professors cannot verify breadth live) but would materially increase ingestion risk and slow every later stage. One state proves the architecture is data-source-agnostic and config-driven (adding a mandi = one config row + one geocode), which is the actual claim being made, not "we have national coverage."

**MVP-ONLY simplification:** mandi-to-mandi and farmer/buyer distance uses plain lat/lon **haversine distance in Python**, not PostGIS (`ST_Distance`/`ST_DWithin`). This is numerically equivalent for the straight-line distances V0.1 itself uses (§3.1, §19 — V0.1 already multiplies straight-line distance by a 1.3× road-distance factor rather than doing real routing), so no behavior is lost, only the spatial-index infrastructure. See Section 13.

---

## 4. Market Data — MVP REQUIRED (with mandatory fallback)

**REQUIRED:** an ingestion layer that can pull from the verified data.gov.in resource identified in V0.1 §4 (`"Current Daily Price of Various Commodities from Various Markets (Mandi)"`), reusing V0.1 §4.2's field mapping as-is (already verified against a live sample by the parent audit's remediation — the MVP does not need to re-derive this).

**REQUIRED — Demo Data Fallback:** `data/demo/mandi_prices.csv`, a multi-month, multi-mandi, multi-crop snapshot large enough to clear the ≥60-observations-in-90-days threshold the parent spec sets for treating an ML model as trustworthy (V0.1 §10). Every API response derived from this file carries `"dataSource": "demo_fixture"` and the dashboard shows a visible **DEMO DATA** badge — this is not optional polish, it is the single most important credibility control in the whole MVP (V0.1 §37's discipline, unchanged).

**MVP-ONLY simplification vs. V0.1:** no scheduled ingestion cron, no incremental daily job, no historical backfill chunking logic (V0.1 §4.1's pagination/retry/backoff machinery). A single on-demand ingestion script is sufficient — it either succeeds and writes into PostgreSQL, or it fails and the system silently uses the demo fixture. Real scheduling is **DEFER TO V0.1**.

**Quarantine / outlier handling:** kept, but simplified to "flag and log," not the full `unmapped_mandis`/`unmapped_commodities` review-table workflow (V0.1 §4.3) — that operational tooling is **DEFER TO V0.1**.

---

## 5. ML Model — MVP REQUIRED (one baseline + one model, not two)

**Baseline:** unchanged from V0.1 §8 — the deterministic weighted formula (`0.4·ModalPrice + 0.3·WMA(7d) + 0.2·RegionalMedian + 0.1·SeasonalIndex`). This is the always-on fallback and the credibility anchor; it costs almost nothing to implement and de-risks every later stage.

**Primary forecasting model — decision: scikit-learn `HistGradientBoostingRegressor`, NOT Prophet, for the MVP.**

| Consideration | Prophet | sklearn HGB | MVP verdict |
|---|---|---|---|
| Install friction on Windows/Antigravity | Requires `cmdstanpy`/a Stan toolchain; a common source of multi-hour setup failures for a first-time installer with no C++ build tooling pre-configured | Pure Python, `pip install scikit-learn`, no external compiler | **sklearn wins** — install risk is unacceptable inside a 3–5 day window |
| Data volume needed to show its strength (seasonality/holiday decomposition) | Needs a full season+ of history to look meaningfully better than a naive model | Learns usable patterns from a smaller feature-engineered demo dataset | **sklearn wins** for MVP-sized demo data |
| Explainability for a professor demo | Very strong (trend/seasonality component plot) | Still explainable via feature importances / per-feature attribution — sufficient for the MVP's "why this price" panel | Roughly even; sklearn's story is simpler to build in the time available |
| Path back to full V0.1 | V0.1 uses Prophet as primary + sklearn as cross-check | Choosing sklearn now means the MVP is literally V0.1's *secondary* model promoted to solo primary — zero architectural rework needed when Prophet is added back in V0.1 | **sklearn wins** — smallest delta to the frozen parent spec |

**Conclusion:** MVP uses Baseline + sklearn `HistGradientBoostingRegressor` only. Prophet is **DEFER TO V0.1** (re-introduced as the second, cross-checking model exactly where the parent spec already puts it — §9, §12). This is not a scope cut relative to V0.1's *intent* (still "one deterministic fallback + one learned model, no black box"), only a temporary reduction from two learned models to one.

Explicitly **REMOVE**: deep learning, LSTM, transformers, reinforcement learning — same reasoning as V0.1 §46 (no data volume or explainability justification), doubly true at MVP scale.

**Temporal validation:** kept, simplified — a single walk-forward train/validation split (not V0.1's three-way train/validation/test with a separate 14-day test window). Still never shuffled; still uses a `TemporalSplitter`-equivalent utility so no accidental random split can creep in. Full three-way split is **DEFER TO V0.1**.

**Acceptance threshold:** kept conceptually (model must beat the naive-lag-1 baseline), simplified to a single global MAE comparison rather than V0.1's per-(crop,mandi)-pair-with-60%-pass-rate rule. Per-pair evaluation granularity is **DEFER TO V0.1**.

---

## 6. Features — MVP REQUIRED (reduced set)

| Group | MVP features | Deferred from V0.1 |
|---|---|---|
| Market | recent modal price (lag_1), rolling_mean_7, price_momentum (7d), volatility_30d | lag_3/14/30, rolling_std_30, full leakage-audit tooling (still no leakage *in principle* — `as_of_date` discipline is kept — but the exhaustive T35-style automated leakage test suite is trimmed, see Section 21) |
| Weather | rainfall (mm), temperature (max °C) — exactly the "one or two meaningful variables" called for | rainfall_anomaly_vs_30yr_avg, temp_anomaly, extreme-weather binary flags — **DEFER TO V0.1** (V0.1 itself already treats the 30yr normal as an ASSUMPTION/approximation; MVP goes one step further and uses raw values only) |
| Demand | order_count_7d, requested_qty_7d → single 0–100 Demand Index (same min-max normalization formula as V0.1 §13, **including the audit's cold-start fix**: `norm(x) = 0` when `max == min`, never divide-by-zero) | demand_growth as a separate term, `unique_buyers` weighting — **DEFER TO V0.1** |
| Spatial | straight-line distance (haversine) farmer↔mandi↔buyer | `regional_price_differential` as a model feature — **DEFER TO V0.1** (folded conceptually into "recent mandi price" for MVP) |

All features remain point-in-time (`as_of_date`-threaded) — this discipline is cheap to keep and is a core credibility claim (V0.1 §48 Q16), so it is **not** cut even though the test coverage around it is reduced.

---

## 7. Price Discovery — MVP REQUIRED (single-term formula, per the audit's correction)

The MVP inherits the **already-corrected** V0.1 formula directly — this is the one place where reusing the audit's fix is not optional, it's the whole point of building on the frozen spec rather than the original pre-audit draft:

```
FairPrice = Baseline + w_forecast × (Forecast − Baseline)
Lower  = FairPrice × (1 − spread)
Upper  = FairPrice × (1 + spread)
```

Weather and demand signals enter **once**, as model input features (Section 6 above), never as a second additive rupee nudge. This is explicitly called out because it is the exact defect (F1, CRITICAL) the parent audit found and fixed — the MVP must not accidentally reintroduce it by building price discovery independently from scratch. `spread()` is simplified from V0.1's full volatility+confidence formula to a single-variable version driven by `volatility_30d` alone (confidence-based widening is **DEFER TO V0.1**, since the MVP's reliability score is already simplified per Section 10 below).

---

## 8. Farmer Protection — MVP REQUIRED

Unchanged in principle from V0.1 §17:
```
FLOOR = 0.85 × Baseline
if FairPrice.Lower < FLOOR → status = "REVIEW REQUIRED"
```
`FarmerDeclaredMinimum` (a user-entered override) is **DEFER TO V0.1** — the MVP has no farmer-facing input form for it, only the professor-facing single dashboard. No MSP or legal pricing claims, same as V0.1 §17/§46.

---

## 9. Logistics — MVP REQUIRED (simplified)

```
CostPerShipment = distance_km × per_km_rate(vehicle_class) + handling_cost
CostPerKg = CostPerShipment / quantity_kg
```
Single vehicle class assumption for MVP (no vehicle-class-selection-by-capacity logic) — vehicle class selection, pooling (V0.1 §19), and spoilage-buffer cost (V0.1 §20) are all **DEFER TO V0.1**. Config-driven per-km rate, explicitly labeled illustrative, exactly as V0.1 already requires.

---

## 10. Final Price Breakdown & Reliability — MVP REQUIRED

```
Buyer Price = Farmer Payout + Logistics Cost/kg + Platform Fee/kg
```
Platform fee: flat % of farmer payout, config-driven, shown as its own line — unchanged from V0.1 §21.

**Prediction Reliability Score (0–100)** — simplified subset of V0.1 §22 (already renamed by the parent audit from "Confidence Score"; MVP keeps the renamed, judge-safe framing):
```
Reliability = 100 × [ 0.35·DataFreshness + 0.30·HistoricalVolume + 0.35·ValidationQuality ]
```
Three components only (data freshness, historical data volume, model validation MAE-vs-baseline performance), each 0–1 normalized. `ModelAgreement`, `MandiAvailability`, `WeatherAvailability`, and the STRESSED-volatility cap rule are **DEFER TO V0.1** — with only one ML model in the MVP (Section 5), a model-agreement term has no second model to compare against, so cutting it is not a shortcut, it's the correct behavior for this scope (mirrors the parent audit's own F5 default-to-neutral logic, just resolved by omission rather than a hardcoded 0.5).

---

## 11. Explainability — MVP REQUIRED

A plain-language panel showing, per prediction: market signal, forecast signal, demand signal, weather signal, logistics, reliability — each one sentence, no causal language ("contributed to" not "caused"), matching V0.1 §23's corrected framing (inputs vs. constraints, not a second pricing mechanism). Full JSON explanation payload with per-sub-score breakdown (V0.1 §23's exact schema) is **DEFER TO V0.1**; the MVP shows the same information as readable text in the dashboard rather than a machine-parseable API contract.

---

## 12. Backend — MVP REQUIRED: FastAPI only, no Node.js

**MVP-ONLY DEVIATION from V0.1 §1.2/§26:** the parent spec requires all frontend traffic to route through Node.js, with FastAPI never trusting a client directly. For this MVP, the Streamlit dashboard calls FastAPI directly.

This is a deliberate, explicitly-flagged deviation, not an oversight: V0.1's Node.js layer exists to own **auth, per-end-user rate limiting, and business workflow** — none of which exist in a single-operator, single-session professor demo. Reintroducing Node.js here would cost real MVP days for zero demo value. When this MVP is grown into V0.1, the Node.js proxy layer is inserted between the existing Streamlit/React frontend and the existing FastAPI service **without changing FastAPI's internal logic at all** — this is additive integration work, not rearchitecture.

FastAPI itself is kept (not cut) because it is genuinely useful even standalone: it gives a real, inspectable, versioned API surface (a live `/predict-price` call is itself a demo credibility point — V0.1 §48 Q7's "server-side computed range, not client-supplied" argument still holds even without Node in front of it).

---

## 13. Database — MVP REQUIRED: PostgreSQL; PostGIS DEFERRED

**PostgreSQL: MVP REQUIRED.** Storing mandi prices, crop config, predictions, and demand data in a real relational database (rather than flat files) is cheap with Docker and materially strengthens the demo's credibility (a professor can be shown a live `psql` query mid-demo — V0.1 §48 Q6/Q16-style trust-building).

**PostGIS: DEFER TO V0.1.** V0.1's actual PostGIS usage is 3 query patterns (nearest-mandi, radius search, pooling-radius clustering — §3.1) operating over a maximum of 5–10 mandis. At that scale, a spatial index provides zero measurable benefit (index or no index, a 10-row distance sort is instant), so PostGIS's *only* MVP-relevant value would be the demo optics of "we use PostGIS" — not worth the extra extension setup, geometry-column schema work, and a new failure mode (V0.1's own risk register, R6, already flags PostGIS as a learning-curve risk) inside a 3–5 day budget. MVP uses plain `latitude`/`longitude` columns and a haversine function in Python. Migrating to `geography(Point,4326)` + GIST indexes later is a schema migration, not a redesign — the distance semantics are already V0.1-equivalent (straight-line × road-distance-multiplier, per V0.1 §19).

---

## 14. Redis — DEFER TO V0.1

A professor demo involves a handful of repeated queries in a single session; PostgreSQL query latency at this data volume (≤10 mandis × 5 crops × a few months of history) is already comfortably under any perceptible threshold. V0.1's cache-hit-rate target (§32, >40% during demo) exists to protect against *judge-panel-scale* concurrent load (10–20 simultaneous requests), which does not apply to a one-professor walkthrough. Adding Redis now would introduce a second infrastructure dependency and a new failure mode (V0.1 §27's Redis-down fallback logic) that has no MVP-stage payoff. Redis is reintroduced in V0.1 exactly where the parent spec already puts it (§24), with no architectural change required upstream.

---

## 15. Frontend — MVP REQUIRED: Streamlit

**Decision: Streamlit**, not React, not plain HTML.

| Option | Dev speed for 1 developer in 3–5 days | Chart/table support | Verdict |
|---|---|---|---|
| React | Slowest — component setup, state management, API client boilerplate, styling all from scratch | Excellent (arbitrary customization) | **Rejected for MVP** — the styling/component investment has no payoff for a single-session internal demo; this is exactly the complexity V0.1's own "no giant black box" and "avoid unnecessary complexity" principles argue against when applied to a 3–5 day budget |
| Plain HTML/JS | Fast to start, but charting/reactivity has to be hand-built or wired to a JS charting lib | Requires manual wiring | **Rejected** — Streamlit gives the same speed with far less boilerplate |
| **Streamlit** | Fastest — a full input-panel + chart + explanation dashboard in a few hundred lines of pure Python, no separate frontend build step, no JS at all | Native support for line charts, bar charts, metrics, dataframes — covers every chart in Section 16 below out of the box | **Chosen** |

React is not removed from the project's future — it is exactly what V0.1 §38 already specifies for the full build, and the MVP's FastAPI backend is the same backend a future React frontend would call. Streamlit is a temporary presentation layer, not a permanent architectural choice.

---

## 16. Visualization — MVP REQUIRED (3 charts, no map)

1. Historical mandi price trend (line chart, actual data)
2. Forecast vs. recent actual price (line chart, model output overlaid on history)
3. Price decomposition (simple bar: farmer payout / logistics / platform fee, matching V0.1 §21's worked-example format)

Map view of mandis/farmers/hubs: **MVP OPTIONAL**, include only if PostGIS/pooling work is somehow ahead of schedule (unlikely, given Section 13's decision) — otherwise **DEFER TO V0.1**.

---

## 17. Explicitly Removed / Deferred from V0.1 for this MVP

| Item | Status | V0.1 reference |
|---|---|---|
| Node.js gateway, auth, rate limiting, circuit breaker | DEFER TO V0.1 (MVP-ONLY DEVIATION, Section 12) | §1, §26, §29 |
| PostGIS spatial queries/indexing | DEFER TO V0.1 | §3.1 |
| Redis caching | DEFER TO V0.1 | §24 |
| Prophet model | DEFER TO V0.1 | §9 |
| Two-model cross-check / ModelAgreement | DEFER TO V0.1 | §12, §22 |
| Logistics pooling, vehicle-class selection, spoilage buffer | DEFER TO V0.1 | §19, §20 |
| Full explanation JSON schema / API contract | DEFER TO V0.1 | §23 |
| Scheduled ingestion, backfill chunking, unmapped-record review tables | DEFER TO V0.1 | §4.1, §4.3 |
| Buyer affordability adjustment | DEFER TO V0.1 | §16 |
| "Where did my ₹100 go?" comparison visualization | DEFER TO V0.1 (needs cited sourcing per R8; not worth doing without it) | §39 |
| Deep learning / RL / LSTM / transformers | REMOVE (not even V0.1) | §46 |
| Kafka / Kubernetes / MLflow / GitHub Actions CI | REMOVE (not even V0.1) | §34, §45, §46 |
| Route optimization / OSRM | REMOVE (not even V0.1) | §19 |
| Production auth, payments, escrow | REMOVE (not even V0.1) | §46 |

---

## 18. Consistency Guarantee

Every simplification above removes *infrastructure or breadth*, never *the correctness of a formula* already fixed by the parent audit. The MVP's price discovery formula, farmer floor formula, and final price breakdown formula are character-for-character the same as the frozen V0.1 spec's corrected versions. This means: once V0.1 development resumes, none of the MVP's core arithmetic needs to be rewritten — only wrapped with the deferred infrastructure listed in Section 17.
