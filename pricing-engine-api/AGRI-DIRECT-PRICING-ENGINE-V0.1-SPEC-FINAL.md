# AGRI-DIRECT-PRICING-ENGINE-V0.1-SPEC-FINAL

## Implementation & Architecture Specification — FROZEN / REMEDIATED

**Status: 🟢 FINAL — audit findings F1, F2, F3, F5, F6 (and related F4/F10 consistency items) resolved. This document is the source of truth for stage-by-stage implementation.**

**Problem Statement:** SIH26033 — Multiple intermediaries reduce farmers' earnings and increase consumer prices.
**Prototype scope:** 1 state, 5–10 mandis, 8–10 crops. Pan-India-compatible architecture, not Pan-India data.

Legend used throughout: **V0.1 REQUIRED** · **DEFER TO V0.2** · **REMOVE FROM V0.1** · **NOT AVAILABLE / FUTURE** · **ASSUMPTION** · **CHANGE REQUIRED**

This is a full remediation of the original `AgriDirect_Pricing_Engine_V0.1_Specification.md`, incorporating every correction from the completed architectural/ML audit. Sections not listed in the changelog below (Section "REMEDIATION CHANGELOG," at the end of this document) are unchanged from the original and remain sound per the audit's own assessment (Section 6, "V0.1 Scope Changes," of the audit: *"No new scope is being proposed to be added... every gap is a specification-precision gap in something already in scope"*).

---

# SECTION 1 — EXECUTIVE ARCHITECTURE

## 1.1 What the Pricing Engine does
- Ingests government mandi price/arrival data and (where available) weather data.
- Maintains a canonical, crop/mandi-agnostic historical price dataset.
- Produces a **Fair Price Range** (farmer payout range + buyer price range), a **Confidence Score**, and an **Explanation payload** for a given crop, quantity, farmer location, and buyer location.
- Computes logistics cost and pooling feasibility.
- Exposes all of the above via a versioned internal REST API (FastAPI) consumed only by the Node.js backend.

## 1.2 What it does NOT do
- It does not process payments, authenticate end users, manage orders, handle chat/voice UI, or own business workflow state (order creation, escrow, delivery tracking) — those remain in Node.js.
- It does not talk directly to Flutter/React. **CHANGE REQUIRED** if any earlier draft assumed direct frontend→FastAPI calls — this must go through Node.js (see Section 26).
- It does not guarantee a legally binding price; every output is a **recommendation**.
- It does not perform real-time nationwide demand sensing — its "demand" is limited to AgriDirect's own order/interest data. **NOT AVAILABLE / FUTURE**: third-party consumer demand data.

## 1.3 Responsibilities and boundaries

| Responsibility | Owner |
|---|---|
| Raw government data ingestion, validation, storage | Pricing Engine (Python) |
| Feature engineering, forecasting, price discovery | Pricing Engine |
| Logistics cost & pooling calculation | Pricing Engine |
| Business workflow (orders, users, payments, auth) | Node.js |
| Caching of hot prediction results | Redis (owned operationally by Node.js infra, used by both) |
| Persistent storage of prices, forecasts, predictions | PostgreSQL + PostGIS (owned by Pricing Engine schema, readable by Node.js via views if needed) |
| User-facing formatting / localization / voice | Flutter / React via Node.js |

## 1.4 Relationships
- **Node.js**: sole caller of the Pricing Engine's REST API. Node forwards farmer/buyer requests, attaches internal auth, and returns results to the frontend.
- **PostgreSQL**: system of record for mandi prices, forecasts, recommendations, logs. Single database, separate schemas (`core`, `pricing`) recommended over separate databases for V0.1 — avoids cross-database joins and duplicate infra.
- **Redis**: low-latency cache for hot predictions, mandi price lookups, and rate limiting. Not a system of record — always reconstructable from PostgreSQL.
- **Frontend**: never calls the Pricing Engine directly; only renders what Node.js returns.
- **External APIs**: Agmarknet/data.gov.in (mandi prices), a weather API (IMD or a commercial provider — **ASSUMPTION**: OpenWeatherMap or Open-Meteo used for prototype since IMD's public API access process is slower to onboard for a hackathon timeline).

## 1.5 Architecture diagram

```mermaid
flowchart TD
    subgraph Client
        A[Flutter Farmer/Aggregator App]
        B[React Web Dashboard]
    end

    A --> C[Node.js API Gateway]
    B --> C

    C -->|internal REST, service token| D[FastAPI Pricing Engine]
    C --> E[(PostgreSQL + PostGIS)]
    C --> F[(Redis)]

    D --> E
    D --> F
    D --> G[Ingestion Worker]
    G --> H[Agmarknet / data.gov.in]
    G --> I[Weather API]

    D --> J[Model Store\n /models on disk]

    C --> K[Razorpay Sandbox]
```

Notes on the improved diagram vs. the prompt's example: PostgreSQL and Redis are shown as shared infrastructure accessed by *both* Node.js (for business data) and FastAPI (for pricing data), rather than exclusively "owned" by the Pricing Engine, since Node also needs read access to prices/forecasts to render dashboards without proxying every read through FastAPI. The ingestion worker is a separate scheduled process, not part of the request path.

---

# SECTION 2 — DATA ARCHITECTURE

Design principle: keep entity count minimal. Reject entities that can be derived (e.g., a `MandiArrival` table is merged into `MandiPrice` rather than a separate table, since arrivals and prices are reported together per Agmarknet record — **CHANGE REQUIRED** relative to the prompt's suggested separate `MandiArrival` entity).

## 2.1 Entity list (final, after normalization)

`Commodity`, `Mandi`, `MandiPrice` (includes arrival qty), `WeatherObservation`, `WeatherForecast`, `BuyerDemandSignal`, `PriceForecast`, `PriceRecommendation`, `LogisticsQuote`, `ModelVersion`, `PredictionLog`.

Removed: separate `MandiArrival` (merged into `MandiPrice`), separate `DemandSignal` (merged into `BuyerDemandSignal` — one row per aggregation window is sufficient for V0.1).

### Commodity
| Field | Type | Null? | Description | Unit | Source | Validation | Index | Example |
|---|---|---|---|---|---|---|---|---|
| id | UUID | No | PK | — | system | — | PK | `c1a2...` |
| name | text | No | canonical crop name | — | config | unique | unique idx | `Tomato` |
| category | text | No | perishability class | — | config | enum: leafy/fruit_veg/root/grain | idx | `fruit_veg` |
| unit | text | No | pricing unit | kg | config | enum(kg,quintal) | — | `kg` |
| shelf_life_days | int | Yes | avg shelf life | days | config/ASSUMPTION | >0 | — | `5` |
| is_active | bool | No | config-driven enable flag | — | config | — | idx | `true` |

### Mandi
| Field | Type | Null? | Description | Unit | Source | Validation | Index | Example |
|---|---|---|---|---|---|---|---|---|
| id | UUID | No | PK | — | system | — | PK | |
| name | text | No | mandi name | — | Agmarknet | not null | idx | `Kolar` |
| state | text | No | state | — | Agmarknet | not null | idx | `Karnataka` |
| district | text | No | district | — | Agmarknet | — | idx | `Kolar` |
| location | geography(Point,4326) | No | lat/lon | — | manual geocode | valid coords | GIST idx | `POINT(78.13 13.13)` |
| agmarknet_code | text | Yes | external id | — | Agmarknet | — | unique idx | `KLR001` |

### MandiPrice (canonical, merges price + arrival)
| Field | Type | Null? | Description | Unit | Source | Validation | Index | Example |
|---|---|---|---|---|---|---|---|---|
| id | bigserial | No | PK | — | system | — | PK | |
| mandi_id | UUID | No | FK Mandi | — | — | FK | idx | |
| commodity_id | UUID | No | FK Commodity | — | — | FK | idx | |
| price_date | date | No | reporting date | — | Agmarknet | not future | idx (composite) | `2026-08-30` |
| min_price | numeric(10,2) | Yes | min price | ₹/quintal | Agmarknet | ≥0 | — | `1800` |
| max_price | numeric(10,2) | Yes | max price | ₹/quintal | Agmarknet | ≥ min_price | — | `2200` |
| modal_price | numeric(10,2) | No | modal price | ₹/quintal | Agmarknet | ≥0 | — | `2000` |
| arrival_qty | numeric(12,2) | Yes | quantity arrived | quintal | Agmarknet | ≥0 | — | `450` |
| ingested_at | timestamptz | No | ingestion time | — | system | — | — | |
| is_flagged_outlier | bool | No | QC flag | — | pipeline | — | idx | `false` |

Unique constraint: `(mandi_id, commodity_id, price_date)`.

### WeatherObservation / WeatherForecast
| Field | Type | Null? | Description | Unit | Source | Validation | Index |
|---|---|---|---|---|---|---|---|
| id | bigserial | No | PK | — | — | — | PK |
| mandi_id (or grid ref) | UUID | No | linked mandi region | — | weather API | FK | idx |
| obs_date | date | No | date | — | API | — | idx |
| rainfall_mm | numeric | Yes | rainfall | mm | API | ≥0 | — |
| temp_min_c / temp_max_c | numeric | Yes | temperature | °C | API | -10..55 | — |
| is_forecast | bool | No | true=forecast row | — | system | — | idx |
| source | text | No | provider name | — | config | — | — |

### BuyerDemandSignal
| Field | Type | Null | Description | Unit | Source |
|---|---|---|---|---|---|
| id | bigserial | No | PK | — | — |
| commodity_id | UUID | No | FK | — | — |
| region_id (mandi or district) | UUID | No | FK | — | — |
| window_start / window_end | timestamptz | No | aggregation window | — | system |
| order_count | int | No | # buyer orders/interest | — | AgriDirect DB |
| requested_qty_kg | numeric | No | total requested qty | kg | AgriDirect DB |
| unique_buyers | int | No | distinct buyers | — | AgriDirect DB |

### PriceForecast
| Field | Type | Null | Description |
|---|---|---|---|
| id | bigserial | PK | |
| commodity_id, mandi_id | UUID | FK |
| forecast_date | date | date being forecast |
| horizon_days | int | 1/3/7 |
| predicted_price | numeric | ₹/quintal |
| lower_bound / upper_bound | numeric | prediction interval |
| model_version_id | UUID | FK ModelVersion |
| generated_at | timestamptz | |

### PriceRecommendation
Stores the full engine output (see Section 15/23) as a denormalized row + JSONB explanation for audit and caching rebuild.

### LogisticsQuote
Stores computed cost per shipment request (see Section 18).

### ModelVersion
| Field | Type | Description |
|---|---|---|
| id | UUID | PK |
| model_type | text | `baseline`/`prophet`/`sklearn` |
| commodity_id | UUID | model is per-crop |
| trained_at | timestamptz | |
| metrics_json | jsonb | MAE, RMSE, sMAPE |
| artifact_path | text | disk path |
| is_active | bool | currently served |

### PredictionLog
Append-only log: `prediction_id, request_json, response_json, model_version_id, latency_ms, created_at`. Used for observability and future training-data leakage audits.

---

# SECTION 3 — POSTGRESQL + POSTGIS SCHEMA

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE core.commodity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL CHECK (category IN ('leafy','fruit_veg','root','grain')),
  unit TEXT NOT NULL DEFAULT 'kg',
  shelf_life_days INT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE core.mandi (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  state TEXT NOT NULL,
  district TEXT,
  location GEOGRAPHY(Point, 4326) NOT NULL,
  agmarknet_code TEXT UNIQUE
);
CREATE INDEX idx_mandi_location ON core.mandi USING GIST(location);
CREATE INDEX idx_mandi_state ON core.mandi(state);

CREATE TABLE pricing.mandi_price (
  id BIGSERIAL PRIMARY KEY,
  mandi_id UUID NOT NULL REFERENCES core.mandi(id),
  commodity_id UUID NOT NULL REFERENCES core.commodity(id),
  price_date DATE NOT NULL CHECK (price_date <= CURRENT_DATE),
  min_price NUMERIC(10,2) CHECK (min_price >= 0),
  max_price NUMERIC(10,2) CHECK (max_price >= min_price),
  modal_price NUMERIC(10,2) NOT NULL CHECK (modal_price >= 0),
  arrival_qty NUMERIC(12,2) CHECK (arrival_qty >= 0),
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_flagged_outlier BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE(mandi_id, commodity_id, price_date)
);
CREATE INDEX idx_price_lookup ON pricing.mandi_price(commodity_id, mandi_id, price_date DESC);

CREATE TABLE pricing.weather_observation (
  id BIGSERIAL PRIMARY KEY,
  mandi_id UUID NOT NULL REFERENCES core.mandi(id),
  obs_date DATE NOT NULL,
  rainfall_mm NUMERIC,
  temp_min_c NUMERIC,
  temp_max_c NUMERIC,
  is_forecast BOOLEAN NOT NULL DEFAULT FALSE,
  source TEXT NOT NULL,
  UNIQUE(mandi_id, obs_date, is_forecast)
);

CREATE TABLE pricing.buyer_demand_signal (
  id BIGSERIAL PRIMARY KEY,
  commodity_id UUID NOT NULL REFERENCES core.commodity(id),
  region_id UUID NOT NULL REFERENCES core.mandi(id),
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  order_count INT NOT NULL DEFAULT 0,
  requested_qty_kg NUMERIC NOT NULL DEFAULT 0,
  unique_buyers INT NOT NULL DEFAULT 0
);

CREATE TABLE pricing.model_version (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_type TEXT NOT NULL,
  commodity_id UUID NOT NULL REFERENCES core.commodity(id),
  trained_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metrics_json JSONB,
  artifact_path TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE pricing.price_forecast (
  id BIGSERIAL PRIMARY KEY,
  commodity_id UUID NOT NULL REFERENCES core.commodity(id),
  mandi_id UUID NOT NULL REFERENCES core.mandi(id),
  forecast_date DATE NOT NULL,
  horizon_days INT NOT NULL,
  predicted_price NUMERIC NOT NULL,
  lower_bound NUMERIC,
  upper_bound NUMERIC,
  model_version_id UUID REFERENCES pricing.model_version(id),
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pricing.price_recommendation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  commodity_id UUID NOT NULL REFERENCES core.commodity(id),
  farmer_location GEOGRAPHY(Point,4326),
  buyer_location GEOGRAPHY(Point,4326),
  quantity_kg NUMERIC NOT NULL,
  farmer_price_low NUMERIC, farmer_price_high NUMERIC,
  buyer_price_low NUMERIC, buyer_price_high NUMERIC,
  confidence NUMERIC,
  market_condition TEXT,
  explanation JSONB,
  model_version_id UUID REFERENCES pricing.model_version(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pricing.logistics_quote (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_id UUID REFERENCES pricing.price_recommendation(id),
  distance_km NUMERIC,
  cost_per_shipment NUMERIC,
  cost_per_kg NUMERIC,
  breakdown JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pricing.prediction_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_json JSONB NOT NULL,
  response_json JSONB NOT NULL,
  model_version_id UUID,
  latency_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 3.1 Spatial query patterns
- **Nearest mandi to farmer**: `ORDER BY location <-> ST_MakePoint(:lon,:lat)::geography LIMIT 5` using the GIST index — O(log n).
- **Radius search** (e.g., mandis within 50 km): `WHERE ST_DWithin(location, ST_MakePoint(:lon,:lat)::geography, 50000)`.
- **Farmer-to-mandi / buyer-to-collection-point distance**: `ST_Distance(a, b)` returns meters directly on `geography` type — no manual haversine needed.
- **Aggregation zones (pooling)**: cluster farmer pickup points within a configurable radius (e.g. 15 km) of a candidate collection-hub mandi using `ST_DWithin`; V0.1 uses mandis themselves as hub candidates rather than computing new hub locations (see Section 19).

## 3.2 ER diagram

```mermaid
erDiagram
    COMMODITY ||--o{ MANDI_PRICE : has
    MANDI ||--o{ MANDI_PRICE : reports
    MANDI ||--o{ WEATHER_OBSERVATION : located_at
    COMMODITY ||--o{ BUYER_DEMAND_SIGNAL : for
    MANDI ||--o{ BUYER_DEMAND_SIGNAL : region
    COMMODITY ||--o{ PRICE_FORECAST : forecasts
    MANDI ||--o{ PRICE_FORECAST : at
    MODEL_VERSION ||--o{ PRICE_FORECAST : produced_by
    MODEL_VERSION ||--o{ PRICE_RECOMMENDATION : produced_by
    PRICE_RECOMMENDATION ||--o| LOGISTICS_QUOTE : includes
    COMMODITY ||--o{ PRICE_RECOMMENDATION : for
```

---

# SECTION 4 — AGMARKNET / DATA.GOV.IN INGESTION CONTRACT

**VERIFIED (F3 remediation)**: the prototype uses the data.gov.in resource **"Current Daily Price of Various Commodities from Various Markets (Mandi)"** (also mirrored under the related "Variety-wise Daily Market Prices Data of Commodity" resource), sourced from the AGMARKNET portal, API-key authenticated. Raw Agmarknet HTML scraping remains explicitly out of scope — fragile and undocumented behavior must not be assumed.

- **Resource landing page**: `https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi`
- **Resource ID observed in sampled records**: `9ef84268-d588-465a-a308-a864a43d0070` (the team must re-confirm this ID against their own generated API key's resource listing before Day 0, since the ID is per-resource, not per-key, but resource catalog entries have occasionally been re-published under new IDs).
- **Auth**: query-param `api-key`; a shared sample key (documented publicly on the OGD portal, rate-limited to 10 records/request) exists for exploration only — production/demo use requires a team-generated key (see Day 0 action item below).
- **Sample record actually returned by the resource** (field names and casing exactly as returned, confirmed live — this supersedes the earlier unverified assumption):

```json
{
  "state": "Keralam",
  "district": "Idukki",
  "market": "Kattappana Market",
  "commodity": "Water Melon",
  "variety": "Other",
  "grade": "Medium",
  "arrival_date": "15/07/2026",
  "min_price": 2000,
  "max_price": 2600,
  "modal_price": 2300
}
```

- **Confirmed present**: `state`, `district`, `market`, `commodity`, `variety`, `grade`, `arrival_date`, `min_price`, `max_price`, `modal_price`. Prices are returned as plain numerics denominated in **₹/quintal** (matching Agmarknet's standard convention — no unit field is included in the payload itself, so the ₹/quintal assumption must stay hardcoded as a documented constant, not inferred per-record).
- **NOT confirmed present**: an `arrival_qty` (arrival quantity) field. It does **not** appear in the sampled payload above. **CHANGE REQUIRED** relative to the original spec, which treated `arrival_qty` mapping as a simple "if present, map directly" — V0.1 must instead treat `MandiPrice.arrival_qty` as **OPTIONAL/FUTURE** for the live feed: populate it only if a per-state/resource variant is confirmed to include it during Day 0 verification; otherwise leave `NULL` for every ingested row and rely on the existing "missing arrival qty → crop-level default, never 0" rule (Section 5). This does not block V0.1, since no downstream formula in Sections 8/15/18/20/21 treats `arrival_qty` as required — only Section 27's "local crop shortage" detection heuristic (`arrival_qty near zero + price spike`) depends on it, and that detector degrades gracefully to "insufficient signal" (not a crash) when the field is NULL, consistent with the fallback-never-fakes-data principle (Section 6).
- `variety` and `grade` are new fields relative to the original mapping table (not previously documented) — mapped as informational/log-only attributes for V0.1 (not written to any `MandiPrice` column, since the schema is variety-agnostic by design); retained in `PredictionLog`/ingestion logs for traceability only.

**Day-0 verification requirement (F3, closes finding)**: before Day 1 of the roadmap (Section 42), the developer must (a) generate a personal API key via the OGD portal's "My Account" flow (this has real approval lead time — see Section 42's Day 0 entry, F8), (b) issue one live request against the resource ID above filtered to the chosen state, and (c) hand-diff the returned field set against this section. If the live field set differs from what's documented here (e.g., a state-specific resource variant with different casing or an `x0020`-encoded field name), update this section before Day 3's ingestion coding begins — do not proceed on the assumption below being correct without that check. Until that live verification is performed by the team, this section is the best-available confirmed mapping (verified via public documentation and third-party API-mirror samples as of this remediation) but is not yet a first-party, team-executed confirmation.

## 4.1 Contract elements
- **Endpoint abstraction**: a single `AgmarknetClient` class wraps HTTP calls; no other module constructs the URL directly.
- **Auth**: API key in query param, stored in env var `AGMARKNET_API_KEY`, never committed.
- **Pagination**: data.gov.in resource API uses `offset`/`limit`; client loops until `records` returned < `limit`.
- **Timeout**: 10s connect, 20s read.
- **Retries**: 3 attempts, exponential backoff (1s, 2s, 4s) on 5xx/timeout only — not on 4xx.
- **Rate-limit handling**: respect `Retry-After` header if present; otherwise back off on repeated 429s.
- **Request logging**: log endpoint, params (minus key), status, latency, record count.
- **Response validation**: Pydantic schema validates every record before it enters the pipeline; invalid records are quarantined, not dropped silently.
- **Deduplication / idempotency**: upsert on `(mandi_id, commodity_id, price_date)` — re-running ingestion for the same day is safe.
- **Incremental ingestion**: daily scheduled job pulls only `price_date = yesterday` (data.gov.in typically lags by a day).
- **Historical backfill**: separate one-time script pulls a configurable date range in chunks (e.g., 30-day windows) to avoid oversized responses.
- **Data freshness**: every `MandiPrice` implicitly carries freshness = `today - price_date`; consumed downstream in the fallback hierarchy (Section 6).

## 4.2 Agmarknet → AgriDirect Canonical Mapping (VERIFIED, F3)

| External Field | Internal Field | Transformation | Unit | Validation |
|---|---|---|---|---|
| `state` | `mandi.state` | trim, title-case | — | not null |
| `district` | `mandi.district` | trim | — | — |
| `market` | `mandi.name` | trim, map via config lookup table to existing `Mandi.id` | — | must resolve to a known/config-seeded mandi; else quarantine |
| `commodity` | `commodity.name` | map via crop-name alias table (naming varies, e.g. "Tomato" vs "Tomato Hybrid") | — | must resolve to active `Commodity`; else quarantine |
| `variety` | *(log-only)* | not persisted to `MandiPrice`; retained in ingestion log for traceability | — | — |
| `grade` | *(log-only)* | not persisted to `MandiPrice`; retained in ingestion log for traceability | — | — |
| `arrival_date` | `mandi_price.price_date` | parse `dd/mm/yyyy` → ISO date | date | must be ≤ today |
| `min_price` | `mandi_price.min_price` | cast numeric, stored as-is (₹/quintal); converted to ₹/kg only at the feature/pricing boundary (§ "Corrected Mathematical Model" unit convention) | ₹/quintal | ≥0 |
| `max_price` | `mandi_price.max_price` | cast numeric, same storage convention | ₹/quintal | ≥ min_price (else swap-correct and flag) |
| `modal_price` | `mandi_price.modal_price` | cast numeric, same storage convention | ₹/quintal | ≥0; if missing, compute `(min+max)/2` and flag as `is_flagged_outlier=false` but `source_derived=true` |
| *(not present in verified sample)* | `mandi_price.arrival_qty` | **OPTIONAL/FUTURE for V0.1**: map directly only if a per-state resource variant is confirmed at Day 0 to include an arrivals field; otherwise leave `NULL` for every ingested row | quintal | ≥0 when present |

**REMOVE FROM V0.1-REQUIRED**: treating `arrival_qty` as a routinely-populated field. It is now documented as optional/best-effort, consistent with the verified payload. All downstream logic that references `arrival_qty` (Sections 5, 7.5, 27) already tolerates `NULL` via the existing fallback rules and requires no further change.

## 4.3 Failure behavior

| Condition | Behavior |
|---|---|
| API unavailable | Skip ingestion run, log ERROR, alert; last known prices remain in DB (freshness naturally degrades and confidence score reacts) |
| Response malformed (schema mismatch) | Quarantine whole batch, log raw payload sample, do not partially ingest |
| Mandi missing / unmapped | Quarantine record, add to a `unmapped_mandis` review table |
| Commodity missing / unmapped | Same as above via `unmapped_commodities` |
| Price missing entirely | Record still ingested with `modal_price = NULL` is **not allowed** (NOT NULL constraint) — such records are quarantined, not inserted |
| Duplicate record | Upsert (idempotent), no error |
| Invalid date | Quarantine record |
| Price obviously erroneous (e.g., ₹0 or 100x jump) | Insert but set `is_flagged_outlier = true`; excluded from training by default (Section 5) |

---

# SECTION 5 — DATA QUALITY PIPELINE

```
Raw Data → Schema Validation → Cleaning → Deduplication → Outlier Detection
→ Missing Value Handling → Normalization → Feature Engineering → Model Dataset
```

| Issue | Rule |
|---|---|
| Missing modal price | If min & max exist, derive `(min+max)/2`, flag `source_derived=true`; else fall back per Section 6 hierarchy |
| Missing min/max | Retain modal price only; downstream range calc widens uncertainty band |
| Missing arrival qty | Treat as NULL; demand/spoilage features that depend on it fall back to crop-level default, never imputed with 0 (0 arrivals is a different real state) |
| Missing weather data | Fall back to nearest-mandi weather, then district average, then seasonal climatology; each fallback logged |
| Duplicate mandi record (same key, re-ingested) | Upsert — last write for that `price_date` wins, ingestion timestamp updated |
| Impossible price (≤0, or > 20x the 30-day median) | **Retained** in DB with `is_flagged_outlier=true`; **excluded from training**; **never deleted** (deletion hides real anomalies like actual shortage spikes) |
| Sudden price spike (>40% day-over-day) | Flagged, not excluded — spikes can be genuine (shortage); training uses robust loss (Huber) rather than exclusion so genuine spikes aren't erased from the model's view |
| Sudden price crash (<-40%) | Same treatment as spike — flagged, retained, included with robust loss |

Decision rule for correct/retain/flag/exclude:
- **Correct**: only clearly mechanical errors (max < min → swap; obviously misplaced decimal, e.g. ₹22000/quintal for tomato when normal range is ₹500–4000 → treat as ₹2200 only if reversible with high confidence, else flag).
- **Retain**: always, unless a record fails a NOT NULL/type constraint (then quarantined pre-insert, not deleted post-insert).
- **Flag**: statistical outliers (>3 MAD from rolling median) — visible to explainability layer.
- **Exclude from training**: flagged outliers only, and only for the *forecasting* model; the baseline (Section 8) still sees raw modal prices since it is a simple statistic, not a learned model sensitive to leakage/skew.

---

# SECTION 6 — MISSING DATA & FALLBACK HIERARCHY

```
Live local mandi (today/yesterday)
      ↓
Recent local mandi (≤7 days old)
      ↓
Nearby mandi (within radius, same commodity, recent)
      ↓
Regional/state aggregate (median across state, recent window)
      ↓
Historical commodity baseline (same mandi, same week-of-year, prior years)
      ↓
Global/default commodity baseline (config-seeded reference price)
```

Improvement over the prompt's version: inserted "Historical commodity baseline (**same mandi**, same season)" *before* the global default, since a mandi-specific seasonal baseline is more accurate than a single global number, and it's cheap to compute from data already ingested.

Every fallback emits:
```json
{ "fallback_level": "nearby_mandi", "reason": "no local price in last 7 days",
  "confidence_penalty": -15, "data_age_days": 4 }
```
This is never hidden from the explanation payload (Section 23) — the UI can choose to soften language, but the engine never silently substitutes.

---

# SECTION 7 — FEATURE ENGINEERING

## 7.1 Price features — **V0.1 REQUIRED**
| Feature | Formula | Source | Window | Unit | Missing-data behavior | Expected relation | Leakage risk |
|---|---|---|---|---|---|---|---|
| lag_1/3/7/14/30 | price[t-n] | mandi_price | n days | ₹/kg | fallback hierarchy | positive/autocorrelated | none (past only) |
| rolling_mean_7/30 | mean(price, window) | mandi_price | 7/30d | ₹/kg | skip NaN, min 3 obs | smooths noise | none |
| rolling_std_7/30 | std(price, window) | mandi_price | 7/30d | ₹/kg | same | proxy for volatility | none |
| price_momentum | (price[t-1]-price[t-7])/price[t-7] | derived | 7d | ratio | 0 if insufficient history | trend signal | none |
| volatility_30d | std/mean over 30d | derived | 30d | ratio | fallback to crop-level avg | risk signal | none |

## 7.2 Seasonal — **V0.1 REQUIRED**
`month`, `week_of_year`, `harvest_flag` (config table per crop: sowing/harvest windows). Festival demand bump — **DEFER TO V0.2**: defensible only with historical order data spanning a festival cycle, which a fresh prototype won't have.

## 7.3 Weather — **V0.1 REQUIRED** (rainfall, rainfall_anomaly_vs_30yr_avg, temp_max, temp_anomaly); extreme weather flags = **V0.1 REQUIRED** (binary: rainfall > 2×monthly avg). IMD 30-year normals dataset for anomaly baselines — **ASSUMPTION**: approximate using the ingested historical window's own mean if a true climatological normal isn't accessible in time.

## 7.4 Spatial — **V0.1 REQUIRED**: `distance_to_mandi_km`, `regional_price_differential` (this mandi's modal price − state median).

## 7.5 Demand — **V0.1 REQUIRED but data-thin**: `order_count_7d`, `requested_qty_7d`, `buyer_count_7d`. `demand_growth` = **V0.1 REQUIRED** (needs only two windows). Deep historical demand elasticity modeling — **FUTURE**.

All features are computed as-of the prediction timestamp only (strict point-in-time joins) to prevent leakage — enforced in code by a single `as_of_date` parameter threaded through every feature function.

---

# SECTION 8 — BASELINE PRICE MODEL

Always-available, zero-ML fallback:

```
Baseline(t) = w1·ModalPrice(mandi, t-1)
            + w2·WeightedMovingAvg(mandi, 7d)
            + w3·RegionalMedian(state, commodity, t-1)
            + w4·SeasonalIndex(commodity, week_of_year)
```
with `w1=0.4, w2=0.3, w3=0.2, w4=0.1` (**ASSUMPTION**, config-driven, tunable without redeploy).

`WeightedMovingAvg` uses exponential weights (more recent days weighted higher): `Σ(price_i · 0.9^i) / Σ(0.9^i)`.

`SeasonalIndex` = ratio of this week's historical average price to the annual average, applied multiplicatively rather than additively (avoids the prompt's flagged anti-pattern of naive additive rules like "rain = +₹5").

This baseline is essential because: (a) it works from day one with zero training, (b) it's fully explainable in one sentence, (c) it is the deterministic fallback required whenever Prophet/ML are unavailable or insufficiently validated (Section 12), (d) it gives judges a transparent reference point to sanity-check the ML models against.

---

# SECTION 9 — FORECASTING MODELS

| Model | Verdict |
|---|---|
| A. Naive/Moving Average | **V0.1 REQUIRED** as the baseline (Section 8) and as the evaluation floor every other model must beat |
| B. Prophet | **V0.1 REQUIRED** — handles seasonality + holidays natively, robust to missing days, interpretable trend/seasonality decomposition suits an explainability-focused judge demo |
| C. Scikit-learn (HistGradientBoostingRegressor) | **V0.1 REQUIRED** as a secondary model — captures nonlinear multi-feature interactions (weather × demand × lag) that Prophet's univariate structure can't |
| XGBoost | **REMOVE FROM V0.1** — HistGradientBoostingRegressor (built into scikit-learn) gives comparable performance on small tabular data without an extra dependency; adds risk for marginal gain |
| Random Forest | Considered, but HistGradientBoosting typically outperforms RF on tabular regression with fewer trees/faster inference — **REMOVE FROM V0.1**, keep as a one-line alternative in config if HGB underperforms in testing |

**V0.1 primary model**: Prophet for the headline forecast (explainable trend/seasonality, works with limited history), with the sklearn model used as a cross-check and as an input to model-agreement-based confidence (Section 22). This satisfies "do not build one giant black box" by keeping two independently interpretable models rather than one ensemble.

---

# SECTION 10 — TIME-SERIES TRAINING STRATEGY

- **Training window**: all available history up to `t-1` (rolling, expands over time).
- **Validation window**: most recent 30 days, held out (walk-forward, not random).
- **Test window**: most recent 14 days, held out after validation.
- **Forecasting horizon**: 1, 3, and 7 days ahead (matches the demo's "7-day forecast" visualization in Section 38).
- **Retraining frequency**: weekly, or on-demand (Section 33) — **not** per-request.
- **Minimum historical data requirement**: 90 days per (mandi, commodity) pair before ML models are trusted; below that, baseline only.
- **Minimum observations**: ≥60 non-null daily prices within the 90-day window (allows some gaps).
- **Missing days**: Prophet handles natively (no explicit fill needed); sklearn features use the fallback hierarchy (Section 6) to fill gaps before feature computation.
- **Mandi closures** (e.g., weekly off-days): treated as expected missingness, not outliers — a `day_of_week` feature lets the model learn the pattern.
- **Sudden regime changes** (e.g., a new policy, a highway opening): **NOT AVAILABLE / FUTURE** to detect automatically; V0.1 relies on the rolling retrain cadence to adapt within ~1–2 weeks, and the volatility indicator (Section 28) flags the interim period as lower-confidence.

Rolling/temporal validation: walk-forward split — train on `[0, t]`, validate on `[t+1, t+30]`, never shuffle. This is enforced by a single `TemporalSplitter` utility so no code path can accidentally call `train_test_split(shuffle=True)`.

---

# SECTION 11 — MODEL EVALUATION

Metrics: **MAE** (primary, interpretable in ₹), **RMSE** (penalizes large misses), **MAPE** (reported but flagged as unreliable near-zero prices — unlikely for these crops but noted), **sMAPE** as a MAPE fallback for volatile periods.

Acceptance criterion (**ASSUMPTION**, tunable): *the candidate model must beat the naive-lag-1 baseline's MAE by at least 8% on the held-out test window, and beat it on at least 60% of individual (mandi, commodity) pairs* — not a single global average, since a global win can mask per-crop failure.

Realistic student-SIH thresholds: MAE within ₹1.5–2.5/kg for high-volume vegetables (tomato/onion/potato) is reasonable; grains (rice/wheat), being far less volatile, should have MAE well under ₹1/kg. Do not promise <5% MAPE across the board — perishable vegetable prices in Indian mandis are genuinely volatile.

Evaluation is run **per-crop, per-mandi, overall, and separately for the top-decile-volatility days** — a model that's accurate in calm periods but bad during spikes should not be silently averaged into a good-looking overall number.

---

# SECTION 12 — MODEL SELECTION

```
Train baseline → Train Prophet → Train ML model → Temporal validation
→ Compare MAE/RMSE (per-crop) → Select model per (crop, mandi) → Store model version
```

Selection is **not** purely training-accuracy based — a model is only eligible if it passes the Section 11 acceptance threshold on the *held-out* test window; the model with the best held-out MAE among eligible models wins, per (crop, mandi) pair (not globally), since some crops may forecast better with Prophet and others with the ML model.

| Situation | Behavior |
|---|---|
| Prophet wins | Prophet becomes active `ModelVersion` for that (crop, mandi) |
| ML wins | sklearn model becomes active |
| Baseline wins (both ML models fail to beat it) | Baseline stays active; flagged in logs for review — this is expected for low-data mandis |
| Data insufficient (<90 days, Section 10) | Baseline only, ML training skipped entirely, not attempted-then-discarded |
| Models disagree strongly (>25% divergence) | Both predictions logged; final forecast used is the eligible model with better *historical* validation MAE, but disagreement lowers the confidence score (Section 22) — this is the "model agreement" signal |

---

# SECTION 13 — DEMAND ENGINE (cold-start rule added, F4)

```
Demand Index (0–100) =
  100 × [ 0.4·norm(order_count_7d) + 0.35·norm(requested_qty_7d) + 0.25·norm(demand_growth) ]
```
where `norm(x)` = min-max normalized against that commodity's trailing 90-day history (so the index is self-calibrating per crop rather than using a fixed global scale).

**Cold-start rule (F4, closes finding)**: AgriDirect has no real transaction history at prototype launch (Sections 37, 39), so the trailing-90-day window will frequently have `max == min` (including the all-zero case), which would otherwise divide by zero. Explicit rule:
```
norm(x) = 0                          if max == min  (including all-zero window)
norm(x) = (x − min) / (max − min)    otherwise
```
When the *entire* trailing-90-day window has zero variance (no order history at all for that commodity/region), the Demand Index is not silently reported as a misleadingly-neutral 0 — instead the response is flagged `"dataSource": "insufficient_demand_history"`, and the Demand Index is **excluded** from the active model's feature set for that prediction (Section 15.1) rather than passed in as a zero value, since a zero-forced demand feature is a different (and false) claim from "no demand signal available." This mirrors the same "never silently substitute" discipline already applied to the price-side fallback hierarchy (Section 6, Section 11 of the corrected fallback hierarchy).

Thresholds (config-driven, **ASSUMPTION**, tunable): `0–29 LOW · 30–59 MODERATE · 60–84 HIGH · 85–100 EXTREME`.

Explicit disclosure requirement: every place the Demand Index is shown, it must be labeled "based on AgriDirect platform order activity" — **never** presented as nationwide consumer demand, since the only signal available is the platform's own transaction data.

---

# SECTION 14 — WEATHER / SUPPLY SIGNAL

```
Weather → Weather features (rainfall_anomaly, temp_anomaly, extreme_flag)
        → Supply/disruption signal (learned feature, not a hardcoded rule)
        → Price model (weather features enter as regular model inputs)
```

Rather than a rule like "rain = +₹5", weather anomalies are simply *features* fed into Prophet (as an external regressor) and the sklearn model; the model learns crop-specific, mandi-specific relationships from historical co-occurrence of weather anomalies and price moves. This is why a learned model is used instead of hardcoded deltas.

Interaction with perishability: for high-perishability crops (category `leafy`/`fruit_veg`), an extreme-weather flag additionally feeds the Spoilage Model (Section 20), not just the price model, since bad weather affects both price *and* transit risk.

Interaction with regional production: **NOT AVAILABLE / FUTURE** — modeling weather impact on *regional yield/production* (rather than just mandi price correlation) would require crop-area and yield datasets not available for this prototype.

Limitations to state explicitly in the demo: weather-price correlation is learned from a short (prototype-length) history and one growing season at most; it should be described as "directional signal," not causal proof.

---

# SECTION 15 — PRICE DISCOVERY ENGINE (CORRECTED, F1)

**Architectural principle (F1 remediation): each real-world signal enters `FairPrice` exactly once, through exactly one mechanism.** Weather, demand, and regional-price signals are model **inputs** (regressors) to the forecasting layer (Section 9), not a second, independent additive adjustment applied again downstream. The original Section 15 formula applied both — once implicitly via the forecast, and again explicitly via `w_demand·DemandAdjustment + w_weather·WeatherAdjustment + w_region·RegionalDifferential` — which double-counted the same signal and made the resulting range systematically over-reactive. That duplication is removed below.

## 15.1 Conceptual pipeline

```
Historical Mandi Data (lags, rolling stats, seasonality)
        +
Weather Features (rainfall anomaly, temp anomaly, extreme flags)     — Section 7.3/14
        +
Demand Features (order_count_7d, requested_qty_7d, demand_growth)    — Section 7.5/13
        +
Regional Market Features (regional_price_differential)               — Section 7.4
        ↓
Forecasting Model (Prophet or sklearn HistGradientBoosting, Section 9)
        ↓
Forecasted Market Price ("Forecast")   ← weather/demand/region already reflected here
        ↓
Price Discovery (this section)  — blends Forecast with the deterministic Baseline
        ↓
Farmer Protection Floor (Section 17)  — hard constraint, not a signal
        ↓
Fair Price Range
```

The **only** place weather/demand/region influence the number is inside "Forecasted Market Price." Everything after that point is either (a) a blend weight against the deterministic baseline, or (b) a downstream constraint (farmer floor, data-quality/freshness confidence penalty, market-deviation/volatility spread) — never a second copy of the same market signal.

## 15.2 Formula

Inputs: mandi baseline (Section 8), forecast (Section 9 — already trained on weather/demand/regional/seasonal features per Sections 7.3–7.5), volatility (Section 7.1), confidence (Section 22).

```
FairPrice = Baseline + w_forecast · (Forecast − Baseline)

Range:
  Lower  = FairPrice × (1 − spread(volatility, confidence))
  Upper  = FairPrice × (1 + spread(volatility, confidence))
```

- `Baseline` — Section 8's deterministic, zero-ML statistic (₹/kg, after the single quintal→kg conversion described in Section 15.4).
- `Forecast` — the point prediction from whichever model is active for this (crop, mandi) per Section 12 (Prophet, sklearn, or Baseline itself if neither is eligible — in which case `Forecast = Baseline` and the second term is 0 by construction, which is the correct behavior for low-data mandis).
- `w_forecast` — the **only** blend weight remaining in this formula (still `0.5` by default, config-driven, tunable without redeploy). It answers one question only: "how much do we let the learned model pull the price away from the deterministic baseline?" This is simpler than the original four-weight formula, removes three now-redundant config values (`w_demand`, `w_weather`, `w_region` — **REMOVE FROM V0.1 config**), and is still explainable in one sentence to a judge: *"we start from a transparent statistical baseline and let the model shift it only as far as the model's own validated accuracy earns it."*
- `spread()` — unchanged from the original spec: `spread = clamp(0.03 + 0.5·volatility_30d + 0.1·(1 − confidence/100), 0.02, 0.15)`. Widens the band when volatility is high or confidence is low; narrows it when both are favorable.

## 15.3 What downstream layers may still do

The Price Discovery output (`FairPrice`, `Lower`, `Upper`) may still be adjusted by legitimate downstream **constraints** — none of which re-inject weather/demand/region as a market signal:

| Layer | Nature | Section |
|---|---|---|
| Farmer protection floor | hard constraint (blocks/flags, does not shift the price upward) | 17 |
| Buyer affordability | display-only adjustment within the already-computed buyer range | 16 |
| Data-quality / freshness | confidence penalty (widens range via `spread()`, never a direct ₹ nudge) | 6, 22 |
| Market deviation / volatility cap | confidence cap + wider `spread()` during STRESSED conditions | 22, 28 |
| Logistics / platform fee | additive, but on the *buyer* side of the split, after `FairPrice` is finalized — not a pricing signal, a cost pass-through | 18, 21 |

None of these are a second copy of the weather/demand/regional signal; they are either hard constraints or cost pass-throughs applied after the market-price question has already been answered by `Forecast`.

## 15.4 Unit convention (closes the Internal Consistency Audit's flagged risk)

All mandi-sourced prices are stored in `pricing.mandi_price` in ₹/quintal (Section 4.2). **Canonical internal unit for every formula in Sections 8, 15–22: ₹/kg.** Conversion happens exactly once, at a single shared utility (e.g. `to_kg(price_quintal) = price_quintal / 100`), imported by every downstream module — feature engineering, baseline, forecasting, price discovery, logistics. No module re-derives or re-converts independently. This utility boundary is now an explicit V0.1 REQUIRED implementation item (Section 35's `app/utils/` module), not just an audit note.

## 15.5 Alternative considered and rejected

The original explicit-nudge design (`+ w_demand·DemandAdjustment + w_weather·WeatherAdjustment + w_region·RegionalDifferential`) remains a valid *alternative* architecture if the team later decides model regressors are too opaque for judge explainability — but it must never be combined with feeding the same signals into Prophet/sklearn as regressors, since that is what caused the double-count. If a future revision prefers standalone nudges, Section 7.3–7.5's weather/demand/regional features must be removed from the model's feature set first. **V0.1 adopts model-regressors-only** (Section 15.1–15.2), since Section 14 already argues correctly that a learned, crop/mandi-specific relationship beats a hardcoded rule, and it removes an artifact a technically sharp judge could otherwise poke a hole in (Section 48, Q17/Q19).

---

# SECTION 16 — BUYER AFFORDABILITY

Inputs used (explicitly *not* inferred personal financial data): declared procurement budget (buyer-entered, optional), requested quantity, buyer's own historical transaction price on the platform, current market price, any explicit order constraints (e.g., "max ₹X/kg").

```
Affordability Score (0–100) =
  100 × clamp( DeclaredBudgetPerKg / FairPrice.Upper , 0, 1.2 ) capped at 100
```
If no budget is declared, Affordability Score defaults to 100 (neutral — does not penalize buyers who simply didn't declare one).

How it influences pricing: Affordability Score can only ever pull the **displayed buyer price toward the lower end of the already-computed buyer range** — it never lowers the farmer payout range. This hard separation is the enforcement mechanism for "farmer economic protection must remain a constraint" (see Section 17): affordability is a *display/negotiation* layer applied strictly on the buyer side of the price split, after the farmer floor (Section 17) has already been applied.

---

# SECTION 17 — FARMER PRICE FLOOR

References (in priority order): recent local market price (mandi baseline), forecast, farmer's own declared minimum acceptable price (if provided). A government MSP-style benchmark is **NOT AVAILABLE / FUTURE** for V0.1 — MSP applies to specific crops (mainly grains) under specific procurement schemes, and asserting MSP applicability without legal verification would be a **CHANGE REQUIRED** on any draft that assumed it applies broadly to vegetables.

```
FLOOR = max( 0.85 × Baseline, FarmerDeclaredMinimum_if_set )
```
If `FairPrice.Lower < FLOOR`:
```
→ status = "PRICE RECOMMENDATION BLOCKED / REVIEW REQUIRED"
→ reason logged (e.g. "recommended price 22% below 7-day mandi baseline")
```
The 15% tolerance band (0.85×Baseline) is an **ASSUMPTION** — configurable per crop, meant to allow legitimate localized price differences without permitting a silent lowball recommendation to reach a farmer.

---

# SECTION 18 — LOGISTICS ENGINE

```
Farmer → Collection point → Buyer
```
```
CostPerShipment =
    PickupCost(distance_farmer_to_hub)
  + LineHaulCost(distance_hub_to_buyer)
  + LoadingUnloadingCost × num_handling_points
  + AggregationFee (fixed, if pooled)
  + TollEstimate(route, if applicable)
  + SpoilageBufferCost   # from Section 20

Where:
  PickupCost / LineHaulCost = distance_km × per_km_rate(vehicle_class)
  vehicle_class chosen by min vehicle capacity ≥ shipment_weight

CostPerKg = CostPerShipment / quantity_kg
```
`per_km_rate` and vehicle capacity/class table are **config-driven** (Section 36), seeded with **ASSUMPTION** rates from typical mini-truck/tempo operating costs for the prototype state, clearly labeled as illustrative until real logistics-partner rates are available. Toll estimation for V0.1 uses a flat per-100km approximation rather than real toll-API integration — **DEFER TO V0.2** for OSRM/real routing + toll APIs.

---

# SECTION 19 — LOGISTICS POOLING

```
Farmer A ─┐
Farmer B ─┼── Collection Hub (existing mandi/config point) ── Buyer
Farmer C ─┘
```
- **Pooling radius**: config default 15 km (`ST_DWithin` on farmer locations around candidate hub).
- **Capacity constraint**: sum of pooled quantities ≤ selected vehicle's capacity; if exceeded, split into multiple shipments (simple bin-packing: sort farmers by distance to hub, fill vehicle greedily) — **not** a full VRP solver.
- **Quantity aggregation**: simple sum per pooling window (e.g., same-day pickups).
- **Distance/route calculation**: straight-line (`ST_Distance`) × a config road-distance multiplier (**ASSUMPTION** 1.3×) rather than real routing for V0.1 — **DEFER TO V0.2**: OSRM-based real road routing.
- **Cost allocation**: pooled shipment cost split pro-rata by quantity contributed (`farmer_i_share = qty_i / total_qty × shipment_cost`) — simplest defensible allocation, avoids distance-based allocation complexity for V0.1.

A greedy nearest-hub, capacity-fill algorithm is explicitly preferred over an optimization solver here per the prompt's own instruction to avoid unnecessary complexity.

---

# SECTION 20 — SPOILAGE MODEL

```
SpoilageRiskScore (0–100) =
  100 × clamp( (TransitHours / (ShelfLifeDays×24)) × WeatherStressMultiplier , 0, 1 )

WeatherStressMultiplier = 1 + 0.3×extreme_heat_flag + 0.2×extreme_rain_flag
```
`ShelfLifeDays` comes from `Commodity.shelf_life_days` (config). `TransitHours` derived from logistics distance/speed assumptions. This explicitly is **not** a laboratory spoilage model — it's a configurable heuristic approximation, labeled as such in every output (`"spoilage_model": "heuristic_v0.1"`), and used only to add a small `SpoilageBufferCost` to logistics (Section 18) and to flag high-risk shipments for prioritized dispatch — not as a scientific claim.

---

# SECTION 21 — FINAL PRICE FORMULA

```
Buyer Price = Farmer Payout + Logistics Cost per kg + Platform Fee per kg
```
Platform Fee: represented as a **transparent flat percentage of Farmer Payout** (e.g., 5%, config-driven, **ASSUMPTION**) shown as its own explicit line item — never bundled invisibly into logistics or into the farmer/buyer spread, so the whole chain is auditable.

### Worked example (Illustrative / Demo Scenario)
```
Crop: Tomato, Qty: 100 kg
Farmer Payout (fair price):      ₹23.50/kg  → ₹2,350
Logistics Cost:                  ₹2.10/kg   → ₹210
Platform Fee (5% of payout):     ₹1.18/kg   → ₹118
------------------------------------------------
Buyer Price:                     ₹26.78/kg  → ₹2,678
```

---

# SECTION 22 — PREDICTION RELIABILITY SCORE (formerly "Confidence Score"; F5/F6)

**Naming (F5/F6 remediation)**: this score is a hand-tuned weighted sum of data-quality and model-agreement sub-signals — it is **not** a statistically calibrated probability that the price is correct. To avoid implying more rigor than the methodology supports, judge-facing copy and the API field should be labeled **"Prediction Reliability Score"** rather than "confidence" wherever the distinction matters to an audience (internal field name `confidence` may remain unchanged in the DB/API for backward compatibility with Section 3/25/40; the display label changes, not the schema).

```
PredictionReliability (0–100) =
  100 × [ 0.25·DataFreshness + 0.20·HistoricalVolume + 0.20·ValidationQuality
        + 0.10·MandiAvailability + 0.10·WeatherAvailability
        + 0.10·ModelAgreement    + 0.05·(1 − MarketVolatility) ]
```

Each sub-component normalized 0–1: `DataFreshness = clamp(1 − age_days/7, 0, 1)`; `HistoricalVolume`, `ValidationQuality`, `MandiAvailability`, `WeatherAvailability` per the existing per-component definitions already implied elsewhere in the spec (Sections 6, 10, 11, 14); `MarketVolatility` = `volatility_30d` (Section 7.1), clamped to [0,1].

**`ModelAgreement` — default rule (F5, closes finding):**
```
ModelAgreement =
  clamp(1 − |ProphetPred − MLPred| / ProphetPred, 0, 1)   if both Prophet and sklearn are active for this (crop, mandi)
  0.5 (neutral default)                                    if only the Baseline is served (Section 12: <90 days history)
```
The neutral default is never silently substituted — every response served in baseline-only mode discloses `"modelAgreementDefault": true` in `fallbacksUsed` (also surfaced at `/model/status`, Section 25/12 corrected API contract below), so the frontend/judge dashboard can distinguish "models genuinely agree" from "no comparison was possible."

**Zero-denominator convention (F10, applies spec-wide):** any ratio-based feature or sub-score with a denominator smaller than ₹0.01 (or otherwise degenerate, e.g. `ProphetPred = 0`) defaults to its neutral/zero value rather than raising or propagating `NaN`, and this substitution is logged. This single convention applies uniformly to `ModelAgreement`, `volatility_30d` (Section 7.1), and any other market-derived ratio in the spec — it is referenced from each formula rather than restated.

**Volatility cap — exact rule (F6, closes finding):** during `STRESSED` market volatility (Section 28, `volatility_30d > 30%`):
```
PredictionReliability = min(computed_reliability, 79)
```
i.e. the score is clamped to the top of the "Medium" band (`60–79`), never forced to a fixed value — this resolves the ambiguity between "cap" meaning a ceiling vs. a fixed override.

Thresholds unchanged: `80–100 High · 60–79 Medium · 40–59 Low · <40 Insufficient` — simple to explain to judges without modification.

Each sub-score is included in the explanation payload (Section 23), so "why is reliability 62%?" is always answerable component-by-component.

---

# SECTION 23 — EXPLAINABILITY (CORRECTED, F1.3)

**Principle (F1.3 remediation)**: the explanation payload must distinguish between (a) **model inputs/signals** that shaped the `Forecast` used in Section 15, and (b) **final pricing constraints** applied afterward (farmer floor, data-quality safeguards, market-deviation limits). The original `drivers[]` array implied weather/demand each contributed an independent, separately-weighted ₹ amount to the final price — that framing is no longer accurate under the corrected Section 15 formula and must not be reproduced.

```json
{
  "recommendedPrice": 21.34,
  "range": { "min": 20.06, "max": 22.62 },
  "reliability": 78,
  "reliabilityBreakdown": {
    "dataFreshness": 0.95, "historicalVolume": 0.8, "validationQuality": 0.85,
    "mandiAvailability": 1.0, "weatherAvailability": 0.7,
    "modelAgreement": 0.9, "marketVolatility": 0.2
  },
  "modelAgreementDefault": false,
  "marketCondition": "MODERATE_DEMAND",
  "priceVolatility": "NORMAL",
  "forecastDrivers": [
    { "factor": "Recent mandi price trend (lags/rolling stats)", "role": "model_input", "attribution": "primary" },
    { "factor": "Demand signal (order activity, 64/100)", "role": "model_input", "attribution": "moderate" },
    { "factor": "Weather: mild rainfall anomaly (+18% vs normal)", "role": "model_input", "attribution": "minor" },
    { "factor": "Regional price differential vs. state median", "role": "model_input", "attribution": "minor" }
  ],
  "pricingConstraints": [
    { "factor": "Farmer protection floor (85% of baseline)", "role": "constraint", "triggered": false },
    { "factor": "Volatility-based range widening", "role": "constraint", "triggered": false }
  ],
  "fallbacksUsed": [],
  "modelVersion": "prophet_v3_tomato_kolar_2026-08-25"
}
```

`forecastDrivers` entries are sourced from the selected model's own feature attribution for that prediction (Prophet's trend/seasonality/regressor component decomposition, or sklearn's per-feature contribution) — a simple, transparent read-off of the model's own internals, not SHAP/LIME (still explicitly rejected as over-engineering for V0.1). This replaces the original spec's implication that weather/demand were independent additive formula terms (Section 15's old `w_demand`/`w_weather`/`w_region`) — they are now correctly attributed as *inputs the model already used*, not a second pricing mechanism. `pricingConstraints` lists the downstream hard constraints from Section 15.3, each with a `triggered` boolean so the UI/judge dashboard can show which, if any, actually bound. No causal language ("rain caused the price to rise") is used anywhere — only correlational/contributory language ("weather signal was among the model's inputs").

---

# SECTION 23.1 — API ADDITIONS (F1/F5 closing the API boundary, folds prior audit §12)

| Method | Path | Change |
|---|---|---|
| POST | `/predict-price` | Response's `forecastDrivers[]` is sourced from model feature attribution (Section 23), not a separate formula term; `pricingConstraints[]` added as a distinct array. Field renamed `confidence` → `reliability` in the response body's headline field (breaking change from the original spec — acceptable pre-implementation; the Node contract in Section 26 and frontend in Section 38 must use the new name from Day 9 onward, not adapted later). |
| GET | `/model/status` | Add `modelAgreementDefault: bool` per (crop, mandi) so the frontend/judge dashboard can distinguish "models genuinely agree" from "no comparison was possible, neutral default used" (F5). |

---

# SECTION 24 — REDIS CACHING

| Key pattern | TTL | Invalidation |
|---|---|---|
| `price:{commodity}:{mandi}:{date}` | 6h | on new ingestion for that date |
| `forecast:{commodity}:{mandi}:{horizon}` | 12h | on retrain (model version change) |
| `recommendation:{commodity}:{farmerGeohash}:{buyerGeohash}:{qtyBucket}` | 15min | on new price ingestion or retrain; short TTL because recommendations combine several fast-changing inputs |
| `demand:{commodity}:{region}` | 1h | on new order events (Node publishes an invalidation event) |

Stale-data behavior: cache misses fall through to PostgreSQL and recompute — Redis is never the sole source; a Redis outage degrades latency, not correctness (see Section 27). Prediction caching uses quantity **buckets** (e.g., 0–50kg, 50–200kg, 200kg+) and geohash-precision-5 location bucketing so cache hit rate stays reasonable despite continuous-valued inputs.

---

# SECTION 25 — FASTAPI SERVICE

| Method | Path | Request | Response | Errors | Timeout |
|---|---|---|---|---|---|
| GET | `/health` | — | `{status, modelVersions, dbOk, redisOk}` | — | 2s |
| POST | `/predict-price` | `{commodityId, quantityKg, farmerLocation, buyerLocation}` | Section 23 payload | 400 invalid crop/coords, 422 validation, 503 insufficient data | 5s |
| GET | `/market-price` | `?commodityId&mandiId` | recent `MandiPrice` rows | 404 no data | 3s |
| GET | `/forecast` | `?commodityId&mandiId&horizonDays` | `PriceForecast` list | 404, 422 | 3s |
| POST | `/logistics/estimate` | `{farmerLocation, buyerLocation, quantityKg, commodityId}` | Section 18 breakdown | 400, 422 | 4s |
| GET | `/price-explanation` | `?predictionId` | stored explanation JSON | 404 | 2s |
| GET | `/model/status` | — | active model versions + metrics per crop | — | 2s |

All request/response models are Pydantic classes shared between endpoints where fields overlap (e.g., a shared `LocationInput` model), so the Node contract (Section 26) and the DB schema (Section 3) can be diffed against one source of truth.

---

# SECTION 26 — NODE.JS ↔ PYTHON CONTRACT

```
Frontend → Node.js → FastAPI
```
Why not frontend → FastAPI directly: Node.js already owns auth, rate limiting per end-user, and business validation (e.g., is this buyer allowed to request this crop); duplicating that in FastAPI would split the security boundary across two services and complicate the "who authenticated this request" story for a hackathon-timeline team.

- **Request flow**: Node validates the business request → calls FastAPI with an internal service token (`Authorization: Bearer <service-token>`, env-configured, rotated manually for V0.1) → FastAPI never trusts end-user identity, only the service token.
- **Timeout**: Node sets a 6s timeout on FastAPI calls (slightly above FastAPI's own 5s prediction timeout).
- **Retry**: 1 retry on network error/5xx only, not on 4xx (client errors are not retried).
- **Circuit breaker**: after 5 consecutive failures within 60s, Node opens the circuit for 30s and serves the **deterministic baseline fallback** (Section 8, replicated as a lightweight Node-side function or a cached last-good baseline) rather than failing the user request outright.
- **Fallback**: baseline-only response, clearly flagged `"degraded": true` to the frontend.
- **Response validation**: Node validates FastAPI's response shape (shared JSON schema) before forwarding to frontend, to catch contract drift early.

---

# SECTION 27 — FAILURE HANDLING

| Failure | Detection | Fallback | User-facing | Logging | Severity |
|---|---|---|---|---|---|
| Agmarknet unavailable | ingestion job error | serve last known prices, freshness penalty in confidence | prices shown, marked "as of Xd ago" | ERROR | Medium |
| Weather API unavailable | ingestion job error | weather features dropped for the day, weight redistributed | no visible change | WARN | Low |
| Redis unavailable | connection error on cache call | read/write straight to PostgreSQL | slower response, no visible break | WARN | Low |
| PostgreSQL unavailable | connection error | FastAPI returns 503, Node circuit-breaks to Node-local baseline if cached | "temporarily using estimated prices" | CRITICAL | High |
| FastAPI unavailable | HTTP error/timeout from Node | Node circuit breaker → baseline fallback | "temporarily using estimated prices" | CRITICAL | High |
| Model unavailable (no active ModelVersion) | FastAPI checks before predict | use baseline (Section 8) | shown as "baseline estimate" | WARN | Medium |
| Insufficient training data | pre-training check | skip ML training, baseline only | no visible change | INFO | Low |
| Malformed API response (external) | schema validation fail | quarantine batch (Section 4) | no visible change | ERROR | Medium |
| Extreme price volatility | volatility indicator > threshold | widen range, cap confidence at "Medium" | "MARKET VOLATILE" badge shown | INFO | Low |
| Local crop shortage | arrival_qty near zero + price spike | flagged in market condition | "LOW SUPPLY" badge | INFO | Low |
| Sudden demand spike | demand index EXTREME | flagged in market condition | "HIGH DEMAND" badge | INFO | Low |
| Stale data (>7 days) | freshness check | fallback hierarchy engaged, confidence penalty | freshness shown explicitly | WARN | Medium |
| Network timeout | client-side timeout | retry once, then fallback | generic retry message | WARN | Medium |
| Invalid coordinates | input validation | 400 error, request rejected | — | INFO | Low |
| Unknown crop | lookup miss | 400 error, request rejected | "crop not supported yet" | INFO | Low |
| Unknown mandi | lookup miss | fall back to nearest known mandi (spatial query) | transparently shown | INFO | Low |

---

# SECTION 28 — EXTREME MARKET EVENTS

A **Market Stress / Volatility Indicator** (derived from `volatility_30d` feature, Section 7) is introduced: `NORMAL` (<15%), `ELEVATED` (15–30%), `STRESSED` (>30%). When `STRESSED`:
- The engine stops trusting the ML/Prophet point forecast as tightly — the Section 15 `spread()` function widens automatically (already wired to volatility), and confidence caps at "Medium" regardless of other sub-scores.
- Sudden crop shortage / flood / drought / heat wave / mandi closure / transport disruption are **not individually modeled as distinct event types** for V0.1 (that would require a labeled events dataset that doesn't exist) — instead, they are all captured indirectly through the same volatility + arrival-quantity + weather-anomaly signals, which is a defensible, honest scope limit to state to judges. **DEFER TO V0.2**: an explicit event-tagging system (e.g., ingesting IMD flood/drought advisories) for more targeted responses.

---

# SECTION 29 — SECURITY

- API keys / secrets: env vars only (`.env`, gitignored), never in source; loaded via a single `config.py`/`config.ts` module.
- Internal FastAPI API: shared-secret bearer token between Node and FastAPI (Section 26); not exposed publicly (bind to internal network / same VPC in deployment, `localhost` in dev).
- PostgreSQL: least-privilege app role (no superuser), password via env, SSL required outside localhost.
- Redis: password-protected (`requirepass`), not publicly bound.
- User input: all coordinates and quantities validated (range checks: lat -90..90, lon -180..180 and must fall within India's bounding box for this prototype; quantity > 0 and below a sane max).
- Rate limiting: Node applies per-user rate limits on prediction requests (protects both FastAPI and external APIs from abuse).
- Logging: no secrets, no raw API keys, no full user PII in FastAPI logs — only IDs.

---

# SECTION 30 — OBSERVABILITY

- Structured JSON logging throughout (not print statements).
- Every request carries a `request_id` (generated by Node, propagated to FastAPI).
- Every prediction carries a `prediction_id` (Section 3's `PredictionLog`), `model_version`, and the ingestion `data_version` (max `ingested_at` used).
- Latency metrics: per-endpoint p50/p95 logged; simplest V0.1 approach is structured log lines aggregated post-hoc rather than a full metrics stack (**DEFER TO V0.2**: Prometheus/Grafana).
- Error rates tracked per endpoint via log aggregation.
- Model performance monitoring: each retrain writes fresh MAE/RMSE into `ModelVersion.metrics_json`; a simple script/notebook can plot metric drift over retrains for the demo.
- Every prediction is traceable end-to-end via `prediction_id` linking `PredictionLog` → `PriceRecommendation` → `ModelVersion` → the specific `MandiPrice`/`WeatherObservation` rows used (recorded in the explanation JSON's `fallbacksUsed`/source list).

---

# SECTION 31 — TESTING STRATEGY

**Unit tests**: price calculation (baseline formula, price discovery formula, farmer floor logic), feature calculation (lags, rolling stats, seasonal index), demand index, logistics calculation, confidence score.

**Integration tests**: Agmarknet ingestion (against recorded fixture responses, not live API), PostgreSQL (schema constraints, upserts), Redis (cache set/get/TTL), FastAPI (endpoint contract tests), Node↔FastAPI (mocked FastAPI, circuit breaker behavior).

**Data tests**: missing values, duplicates, invalid prices, extreme values, stale data — each as a fixture dataset run through the Section 5 pipeline with asserted outcomes.

**ML tests**: leakage detection (assert no feature uses `t+1` or later data), temporal validation (assert splitter never shuffles), model reproducibility (same seed → same metrics within tolerance), baseline comparison (assert acceptance threshold logic).

**End-to-end**: farmer → crop selection → quantity → location → market data → prediction → logistics → final quote, run against a seeded demo dataset.

### Representative V0.1 test cases (40 total; IDs T01–T40)

| ID | Scenario | Input | Expected | Pass/Fail criteria |
|---|---|---|---|---|
| T01 | Happy path prediction | valid tomato/mandi/qty/locations | 200, full explanation payload | fields present, range.min < range.max |
| T02 | Unknown crop | commodityId not in DB | 400 | error body has clear message |
| T03 | Invalid coords | lat=999 | 422 | rejected before reaching pricing logic |
| T04 | Missing modal price, min/max present | mandi_price row with modal NULL | derived `(min+max)/2`, flagged | `source_derived=true` in DB |
| T05 | All prices missing for mandi | empty mandi_price for last 30d | fallback hierarchy engaged to nearby mandi | `fallbacksUsed` non-empty, confidence reduced |
| T06 | Duplicate ingestion same day | same record ingested twice | single row (upsert) | row count unchanged, `ingested_at` updated |
| T07 | Outlier price (100x median) | injected bad record | inserted, `is_flagged_outlier=true`, excluded from training | training set excludes row |
| T08 | Sudden 45% price spike | real-looking spike | retained, flagged, included in training with robust loss | included, not deleted |
| T09 | Insufficient history (<90d) | new mandi/commodity pair | baseline used, ML training skipped | `modelVersion` = baseline |
| T10 | Model disagreement >25% | mocked divergent predictions | confidence reduced via modelAgreement term | confidence lower than a no-disagreement control case |
| T11 | Baseline formula correctness | known fixed inputs | matches hand-calculated value | exact match within rounding |
| T12 | Weighted moving average correctness | known price series | matches formula | exact match |
| T13 | Demand index bounds | extreme synthetic demand | index clamped to [0,100] | no out-of-range values |
| T14 | Confidence sub-scores sum correctly | fixed sub-inputs | matches weighted formula | exact match |
| T15 | Farmer floor triggers block | forced low recommendation | status = BLOCKED/REVIEW | response includes reason |
| T16 | Farmer floor not falsely triggered | normal recommendation | status normal | no false block |
| T17 | Affordability never lowers farmer range | low declared budget | farmer_price unaffected, buyer display adjusted only | farmer range identical with/without budget field |
| T18 | Logistics cost formula | known distance/qty | matches hand calc | exact match |
| T19 | Vehicle class selection | qty exceeds one vehicle class | next larger class selected | correct class chosen |
| T20 | Pooling capacity split | 3 farmers exceeding capacity | split into 2 shipments | shipment count and totals correct |
| T21 | Pooling cost allocation | pro-rata by qty | shares sum to total cost | sum matches within rounding |
| T22 | Spoilage score bounds | extreme transit time | clamped to [0,100] | no out-of-range |
| T23 | Final price formula | known payout/logistics/fee | buyer price = sum | exact match |
| T24 | Nearest-mandi spatial query | known coordinates | correct nearest mandi returned | matches expected mandi id |
| T25 | Radius search | known radius | correct mandi set | matches expected set |
| T26 | Cache hit returns identical payload | repeat identical request within TTL | same `predictionId`/payload | cache-served flag true, values equal |
| T27 | Cache invalidation on new ingestion | ingest new price, re-request | different (fresher) payload | freshness improved |
| T28 | Redis down → PostgreSQL fallback | Redis connection killed | request still succeeds (slower) | 200 response, degraded flag absent (correctness preserved) |
| T29 | PostgreSQL down | DB connection killed | 503 from FastAPI, Node circuit-breaks | Node returns baseline with `degraded:true` |
| T30 | FastAPI down | service killed | Node circuit breaker opens after 5 failures | fallback served, no user-facing 500 |
| T31 | Agmarknet API down | mocked failure | ingestion skipped gracefully, no crash | job exits cleanly, ERROR logged |
| T32 | Malformed Agmarknet response | invalid schema fixture | batch quarantined | no partial insert |
| T33 | Unmapped mandi in response | new mandi name | quarantined to review table | appears in `unmapped_mandis` |
| T34 | Temporal split correctness | fixture dataset | validation window strictly after training window | no date overlap |
| T35 | No leakage in features | fixture dataset | feature values at time t don't reference t+1 data | assertion passes |
| T36 | Model reproducibility | same seed, same data | metrics within tolerance across two runs | delta < defined epsilon |
| T37 | Retrain versioning | trigger retrain | new `ModelVersion` row, old marked inactive | exactly one active version per (crop) |
| T38 | Explanation payload completeness | any prediction | all required fields present | schema validation passes |
| T39 | End-to-end demo flow | seeded demo dataset, full flow | final quote produced with all 15 stages (Section 41) | all stage outputs present and consistent |
| T40 | Rate limiting | burst of requests from one user | requests beyond limit rejected (429) | rate limiter engages correctly |

### Remediation test cases (F1–F6; added by this audit-remediation pass)

| ID | Scenario | Input | Expected | Pass/Fail criteria |
|---|---|---|---|---|
| T41 | Formula double-count regression (F1) | Fixed baseline/forecast inputs where weather/demand/regional features are also present in the model's feature set | `FairPrice` matches the corrected single-term Section 15 formula (`Baseline + w_forecast·(Forecast−Baseline)`) exactly, NOT the original 4-term additive-nudge formula | Exact match; this test guards against F1 ever being silently reintroduced by a future edit |
| T42 | Demand Index cold start (F4) | Trailing 90-day platform order window is entirely empty (new commodity/region) | `norm(x) = 0` returned, no exception; response flagged `"dataSource": "insufficient_demand_history"`; Demand Index excluded from the Forecast's feature set for that prediction rather than silently zero-forced | No NaN/exception; flag present; excluded (not zeroed) |
| T43 | Reliability score, baseline-only mode (F5) | No Prophet/ML model trained for a (crop, mandi) pair (<90 days history) | `ModelAgreement = 0.5` (neutral default), `"modelAgreementDefault": true` present in `fallbacksUsed` and at `/model/status` | Exact default value; disclosure present in both locations |
| T44 | Volatility cap exact rule (F6) | `STRESSED` volatility (`volatility_30d > 30%`) with a computed pre-cap reliability of 91 | Returned reliability == 79 | Exact match to `min(computed, 79)` rule, not a fixed override value |
| T45 | Section 41 worked example as fixture (F2) | `PRICE-E2E-001` fixture inputs (Section 41.1) | Every intermediate value (baseline, fair price, spread, range, floor check, logistics, platform fee, buyer price, final split) matches Section 41's recomputed worked example to the stated tolerance | Exact match on deterministic values; ±0.01 on rounded range bounds; this is the permanent regression guard for F2 |
| T46 | Zero-denominator ratio features (F10) | Flat 30-day price series (`std = 0`, so `volatility_30d` denominator → 0) | `volatility_30d = 0` returned (neutral default), no exception; same convention applied to `ModelAgreement` when `ProphetPred = 0` | No exception; matches the Section 22 zero-denominator convention |

---

# SECTION 32 — PERFORMANCE REQUIREMENTS

| Metric | SIH prototype target | Future production target |
|---|---|---|
| Prediction latency (p95) | < 800ms (cache miss), < 100ms (cache hit) | < 300ms cache miss |
| API latency (Node → FastAPI round trip) | < 1s | < 400ms |
| Cache hit rate | > 40% during demo (small, repeated demo query set) | > 70% |
| Ingestion time (daily incremental) | < 2 min | < 30s |
| Model training time (per crop) | < 3 min on a laptop CPU | GPU-accelerated batch retrain, minutes for all crops |
| Concurrent requests | 10–20 (judge panel + demo) | hundreds |

These are deliberately modest — a hackathon demo does not need enterprise-scale numbers, and overstating them invites judge scrutiny that can't be backed up live.

---

# SECTION 33 — MODEL RETRAINING

- **Scheduled retraining**: weekly cron (e.g., Sunday night) per (crop) across all its mandis.
- **Trigger conditions**: also allow manual on-demand retrain (CLI command) for demo-day freshness, and an automatic trigger if 14+ new days of data have accumulated since the last training run for a given crop.
- **Model versioning**: every training run creates a new `ModelVersion` row; only one `is_active=true` per (model_type, commodity).
- **Rollback**: activating a previous `ModelVersion` id is a single UPDATE — no retraining needed to roll back.
- **Validation before deployment**: a newly trained model only flips `is_active=true` if it passes the Section 11 acceptance threshold; otherwise the previous active model stays active and the failed run is logged for review.
- Training and inference are strictly separate processes: a scheduled/CLI training script writes model artifacts to disk + DB metadata; FastAPI's request path only ever *loads and applies* an already-active model — it never trains on the fly.

---

# SECTION 34 — MLOPS STRUCTURE

| Tool | Verdict |
|---|---|
| Git | **REQUIRED FOR V0.1** — non-negotiable, versioning code and this spec itself |
| Model artifact storage (local disk under `/models`, path recorded in `ModelVersion.artifact_path`) | **REQUIRED FOR V0.1** |
| Experiment tracking (basic: metrics stored in `ModelVersion.metrics_json`) | **REQUIRED FOR V0.1** (lightweight, DB-based — not a separate tool) |
| MLflow | **OPTIONAL** — nice if the team has time, but the DB-based metrics table already satisfies the traceability requirement; adds setup overhead not justified for a 2-week build |
| Docker | **OPTIONAL** — useful for consistent demo-day environment reproduction, but not required if the team is comfortable running services directly; recommended if time allows on Day 1 |
| GitHub Actions (CI) | **DEFER TO V0.2** — nice-to-have automated test runs, but manual `pytest` runs are sufficient for a 2-week sprint |

---

# SECTION 35 — PROJECT DIRECTORY STRUCTURE

```
pricing-engine/
│
├── app/
│   ├── api/            # FastAPI route handlers only — thin, delegate to services
│   ├── core/            # config loading, logging setup, DB/Redis connections
│   ├── models/           # Pydantic request/response + ORM models
│   ├── services/         # orchestration: predict_price(), get_forecast(), etc.
│   ├── forecasting/       # baseline, prophet, sklearn model wrappers, training scripts
│   ├── pricing/           # price discovery, farmer floor, affordability, confidence
│   ├── logistics/         # logistics cost, pooling, spoilage
│   ├── features/          # feature engineering functions, fallback hierarchy
│   ├── ingestion/         # AgmarknetClient, weather client, ingestion jobs, validators
│   └── utils/             # geo helpers, date helpers, shared constants
│
├── tests/                # mirrors app/ structure
├── data/                  # local fixtures, demo dataset (Section 37)
├── models/                # trained model artifacts (gitignored, per-crop subfolders)
├── scripts/                # backfill, retrain-on-demand, seed-db
├── configs/                # crop config, pricing weights, logistics rates (YAML/JSON)
├── notebooks/              # exploratory analysis, metric-drift plots for demo
└── requirements.txt
```
Each directory's single responsibility keeps the "no giant black box" principle enforced structurally: `pricing/` cannot import model-training internals from `forecasting/` beyond its published prediction interface.

---

# SECTION 36 — CONFIGURATION MANAGEMENT

Configurable (never hardcoded), via `configs/*.yaml` loaded at startup and cached in memory (with a manual reload endpoint for demo-day tuning):

crop parameters (shelf life, category, unit), model parameters (train window, acceptance threshold %), pricing weight (Section 15's single `w_forecast` — **REMOVE FROM V0.1 config**: `w_demand`, `w_weather`, `w_region`, which no longer exist as separate config values after the F1 remediation), reliability thresholds/weights (Section 22), logistics rates (per-km, per-handling, vehicle classes/capacities), spoilage assumptions (`WeatherStressMultiplier` coefficients), cache TTLs (Section 24), API timeouts (Sections 25/26), farmer floor tolerance (Section 17), pooling radius (Section 19), platform fee % (Section 21), zero-denominator epsilon convention (Section 22, F10).

---

# SECTION 37 — DEMO DATA STRATEGY

- **Live mode**: real Agmarknet + weather API calls, as designed in Sections 4/14.
- **Demo fallback mode**: a pre-ingested, versioned snapshot dataset (`data/demo_snapshot.sql` or CSV) covering the chosen state's 5–10 mandis and 8–10 crops across a realistic multi-month window, loadable in seconds, used automatically if live ingestion fails during the demo window or on explicit `DEMO_MODE=true` env flag.
- Every response derived from demo/synthetic data carries an explicit `"dataSource": "demo_snapshot"` field, and the frontend renders a visible "Demo Data" badge — synthetic data is never presented as live government data.
- The demo snapshot is real historical Agmarknet data captured in advance (not fabricated numbers) wherever possible, which keeps the "never fabricate government data" principle intact even in fallback mode; only clearly-synthetic elements (e.g., simulated buyer demand, since AgriDirect itself is new and has no real order history yet) are labeled **Illustrative / Demo Scenario**.

---

# SECTION 38 — FRONTEND VISUALIZATION

**Farmer app**: fair price range (large, primary), confidence badge, simple demand/weather icons, one-tap "why this price?" expandable explanation, 7-day mini forecast sparkline.

**Buyer dashboard**: mandi price trend chart, fair-price range, logistics cost breakdown, pooling status/savings, map of nearby farmers/collection hubs.

**SIH judge dashboard**: everything above plus confidence sub-score breakdown, model version/metrics panel, the "Where did my ₹100 go?" comparison (Section 39), and a live/demo-mode indicator.

Recommended components: line chart (price trend + forecast band), gauge (confidence), badge (market condition), stacked bar (₹ breakdown: payout/logistics/fee), map (`places_map`-style with hub + pooled farmers), savings callout card.

---

# SECTION 39 — "WHERE DID MY ₹100 GO?" DEMONSTRATION

Two side-by-side stacked bars, clearly labeled **Illustrative / Demo Scenario** (since AgriDirect has no real transaction data yet to empirically measure typical intermediary margins):

```
Traditional Chain (illustrative)        AgriDirect
Farmer share:      ~55-60%              Farmer share:      ~88%
Intermediary/logistics margins: ~35-40% Logistics:         ~8%
Retailer margin:   remainder             Platform fee:      ~5%
```
Exact traditional-chain percentages should be sourced from published agricultural-economics studies where possible during the actual hackathon build (cited, not invented) — until such a citation is added, the visualization must keep the "Illustrative" label and avoid stating them as fact.

---

# SECTION 40 — API EXAMPLE

**Price prediction request**
```json
POST /predict-price
{ "commodityId": "c-tomato", "quantityKg": 100,
  "farmerLocation": {"lat": 13.13, "lon": 78.13},
  "buyerLocation": {"lat": 12.97, "lon": 77.59} }
```
**Price prediction response**: see Section 23's payload, extended with `farmerPayout`, `buyerPrice`, `logisticsCostPerKg`, `platformFeePerKg`.

**Logistics request**
```json
POST /logistics/estimate
{ "farmerLocation": {...}, "buyerLocation": {...}, "quantityKg": 100, "commodityId": "c-tomato" }
```
**Logistics response**
```json
{ "distanceKm": 68.4, "vehicleClass": "mini_truck",
  "costPerShipment": 812, "costPerKg": 8.12,
  "breakdown": {"pickup": 210, "lineHaul": 480, "handling": 60, "spoilageBuffer": 62} }
```
**Market intelligence response**: recent price series + volatility + market condition for a (crop, mandi).

**Price explanation response**: Section 23 payload retrieved by `predictionId`.

**Error response**
```json
{ "error": "VALIDATION_ERROR", "message": "quantityKg must be > 0", "requestId": "req_8f2..." }
```

---

# SECTION 41 — END-TO-END EXAMPLE (RECOMPUTED, F2)

**All figures below are recomputed by hand against the corrected Section 15 formula. Every intermediate step is arithmetically verified (Section 41.1 shows the checked arithmetic). This example is frozen as test fixture `PRICE-E2E-001` (Section 41.1) and must not be edited without re-running the arithmetic check.**

```
Crop: Tomato | Quantity: 500 kg | Farmer: Kolar rural | Buyer: Bengaluru
Nearest mandis: Kolar (12km), Chintamani (45km), Bengaluru (68km)
Canonical internal unit: ₹/kg (mandi source data is ₹/quintal, converted once at ingestion boundary, Section 15.4)

STEP 1 — Mandi observations (raw, ₹/quintal → converted ₹/kg)
  Kolar modal price (t-1):        ₹2,050/quintal  → ₹20.50/kg
  Kolar 7-day weighted moving avg:                 ₹19.80/kg
  Regional (state) median, same commodity/date:     ₹20.10/kg
  Seasonal reference price (week-of-year index):     ₹20.00/kg
  Data freshness: modal price is 1 day old (fresh)

STEP 2 — Weather signal (model INPUT, not a separate ₹ term)
  Rainfall anomaly: +18% vs 30-day-window mean (no true 30yr normal available, Section 7.3 ASSUMPTION)
  Extreme-weather flag: false
  → fed into Prophet as an external regressor (Section 14)

STEP 3 — Demand signal (model INPUT, not a separate ₹ term)
  order_count_7d = 12, requested_qty_7d, demand_growth computed → Demand Index = 64 (MODERATE-HIGH, Section 13)
  → fed into Prophet/sklearn as regressor features (Section 7.5)

STEP 4 — Regional signal (model INPUT, not a separate ₹ term)
  regional_price_differential = Kolar modal (20.50) − state median (20.10) = +0.40 ₹/kg
  → fed into the model as a feature (Section 7.4)

STEP 5 — Baseline (Section 8, deterministic, no ML)
  Baseline = 0.4×20.50 + 0.3×19.80 + 0.2×20.10 + 0.1×20.00
           = 8.20 + 5.94 + 4.02 + 2.00
           = ₹20.16/kg

STEP 6 — Model forecast (Section 9/12; Prophet selected for this crop/mandi pair, already trained on Steps 2–4's features)
  Forecast (7-day-ahead) = ₹21.20/kg, validation MAE = ₹1.10/kg, model = prophet_v3_tomato_kolar

STEP 7 — Price Discovery (Section 15, CORRECTED — single blend term only)
  FairPrice = Baseline + w_forecast × (Forecast − Baseline)
            = 20.16 + 0.5 × (21.20 − 20.16)
            = 20.16 + 0.5 × 1.04
            = 20.16 + 0.52
            = ₹20.68/kg

STEP 8 — Reliability sub-scores → volatility_30d = 0.12, PredictionReliability = 78 (Medium-High)
  spread = clamp(0.03 + 0.5×volatility_30d + 0.1×(1 − reliability/100), 0.02, 0.15)
         = clamp(0.03 + 0.5×0.12 + 0.1×(1 − 0.78), 0.02, 0.15)
         = clamp(0.03 + 0.06 + 0.1×0.22, 0.02, 0.15)
         = clamp(0.03 + 0.06 + 0.022, 0.02, 0.15)
         = clamp(0.112, 0.02, 0.15)
         = 0.112

STEP 9 — Fair price range
  Lower = FairPrice × (1 − spread) = 20.68 × 0.888 = ₹18.36/kg   (18.36384, rounded)
  Upper = FairPrice × (1 + spread) = 20.68 × 1.112 = ₹23.00/kg   (22.99616, rounded)

STEP 10 — Farmer protection floor (Section 17, hard constraint — not a signal)
  FLOOR = max(0.85 × Baseline, FarmerDeclaredMinimum_if_set) = 0.85 × 20.16 = ₹17.14/kg  (no declared minimum set)
  Check: FairPrice.Lower (18.36) ≥ FLOOR (17.14) → NOT BLOCKED, margin = +₹1.22/kg above floor

STEP 11 — Farmer payout
  Farmer payout = FairPrice = ₹20.68/kg → ₹20.68 × 500 = ₹10,340 for 500 kg

STEP 12 — Logistics (Section 18; 68 km Kolar→Bengaluru, mini-truck vehicle class, incl. spoilage buffer)
  Logistics cost = ₹8.40/kg → ₹8.40 × 500 = ₹4,200

STEP 13 — Platform fee (Section 21; 5% of Farmer Payout, transparent line item)
  Platform fee = 0.05 × 20.68 = ₹1.03/kg → ₹1.03 × 500 = ₹515

STEP 14 — Final buyer price
  Buyer Price = Farmer Payout + Logistics Cost + Platform Fee
              = 20.68 + 8.40 + 1.03
              = ₹30.11/kg → ₹30.11 × 500 = ₹15,055

STEP 15 — Final split (verified: 10,340 + 4,200 + 515 = 15,055 ✓ exact)
  Farmer share:     ₹10,340 (68.68% of buyer price)
  Logistics share:  ₹4,200  (27.89% of buyer price)
  Platform share:   ₹515    (3.42% of buyer price)
  (percentages sum to 99.99% due to 2-decimal rounding of per-kg figures — acceptable display rounding, not a computation error; the underlying ₹ totals reconcile exactly.)
```

## 41.1 Test fixture `PRICE-E2E-001` (F2.1, promotes this example into a permanent regression test — see Section 31 T45)

```yaml
fixture_id: PRICE-E2E-001
inputs:
  commodity: Tomato
  quantity_kg: 500
  mandi_modal_price_quintal: 2050        # t-1
  mandi_wma_7d_kg: 19.80
  regional_median_kg: 20.10
  seasonal_reference_kg: 20.00
  prophet_forecast_kg: 21.20
  volatility_30d: 0.12
  prediction_reliability: 78
  farmer_declared_minimum: null
  logistics_distance_km: 68
  logistics_cost_per_kg: 8.40
  platform_fee_pct: 0.05
  w_forecast: 0.5
expected_intermediate_values:            # tolerance: exact match unless noted
  baseline_kg: 20.16
  fair_price_kg: 20.68
  spread: 0.112
  range_lower_kg: 18.36                  # tolerance: ±0.01 (rounding)
  range_upper_kg: 23.00                  # tolerance: ±0.01 (rounding)
  farmer_floor_kg: 17.14
  floor_blocked: false
expected_final_values:
  farmer_payout_total: 10340
  logistics_total: 4200
  platform_fee_total: 515
  buyer_price_total: 15055
tolerance_note: >
  All values above are deterministic (no live ML training in the test),
  since prophet_forecast_kg is supplied directly as a fixed input rather than
  produced by a live model run. This isolates Section 15's arithmetic from
  model-training nondeterminism, per Section 10's temporal-validation
  reproducibility requirement (T36 covers model-level reproducibility
  separately).
```

---

# SECTION 42 — 10–14 DAY AI-AGENTIC IMPLEMENTATION ROADMAP (Day 0 added, F8/F11)

Each day: objective, tasks, files/modules, dependencies, AI-agent prompt (see reusable template in Section 43), developer verification, acceptance criteria, tests, expected output.

| Day | Objective | Key files/modules | Acceptance criteria |
|---|---|---|---|
| **0 (pre-sprint, new — F8/F3)** | Request data.gov.in API key (real approval lead time — do this before anything else); confirm the resource ID in Section 4; pull one live sample and hand-verify Section 4.2's field mapping against it | none (no code) | live sample obtained; Section 4.2 confirmed or corrected before Day 1 begins |
| 1 | Spec finalized, repo scaffolded, environments set up (Python venv, Node, Postgres+PostGIS, Redis running locally) | repo skeleton (Section 35), `.env.example`, `requirements.txt`, `docker-compose.yml` if used | `pytest` runs (even with 0 tests), FastAPI `/health` returns 200 locally |
| 2 | DB schema live | `configs/`, migration scripts (Alembic recommended), Section 3 SQL applied | all tables created, constraints verified with a bad-insert test |
| 3 | Agmarknet ingestion working against real API for the chosen state/mandis | `app/ingestion/` | daily job populates `mandi_price` for real mandis; T31/T32/T33 pass; field mapping matches Day 0's verified sample |
| 4 | Data cleaning + feature engineering | `app/features/` | Section 5 pipeline runs on ingested data; T04–T08 pass |
| 5 | Baseline model | `app/forecasting/baseline.py` | T11/T12 pass; baseline callable end-to-end |
| 6 | Prophet model + temporal validation | `app/forecasting/prophet_model.py` | passes Section 11 acceptance threshold on at least 3 crops (F11: explicitly allowed to spill 2–3 hrs into Day 7 morning if real data is messier than fixtures) |
| 7 | Scikit-learn model | `app/forecasting/sklearn_model.py` | T34–T36 pass; model selection logic (Section 12) working (F11: same spill allowance; if both Day 6 and 7 slip, compress Day 8's weather-signal plumbing rather than Day 9's pricing logic) |
| 8 | Demand + weather signals wired in as **model regressors** (Section 15.1 — not as separate §15 nudge terms) | `app/features/demand.py`, `app/features/weather.py` | T13, T42 pass; weather anomaly features populated |
| 9 | Price discovery (corrected Section 15 formula) + reliability score (Section 22) + explainability (Section 23) | `app/pricing/` | T14–T17, T38, T41, T43, T44, T45 pass; `/predict-price` returns full payload matching `PRICE-E2E-001` |
| 10 | Logistics + pooling + spoilage | `app/logistics/` | T18–T22 pass |
| 11 | FastAPI endpoints finalized, Redis caching wired | `app/api/` | all Section 25 endpoints live; T26–T28 pass |
| 12 | Node.js integration (proxy, circuit breaker, contract validation) | Node service layer | T29/T30 pass; frontend can call through Node successfully |
| 13 | Frontend visualization (Section 38 components) | React/Flutter components | judge dashboard renders live data; demo mode toggle works |
| 14 | Testing + demo hardening | full test suite, demo snapshot (Section 37) | T01–T46 pass; demo runs fully offline via `DEMO_MODE=true` |

For each day, the developer verification step is: run that day's test subset, manually hit the new endpoint/feature with a real or fixture request, and diff the output against the `PRICE-E2E-001` fixture (Section 41.1) where applicable. No day count increase beyond the original plan is required — Day 0 is pre-sprint prep, not an additional build day; if the team wants a true in-sprint buffer, insert it after Day 7.

---

# SECTION 43 — AI CODING AGENT STRATEGY

Rules: read the spec first; never redesign architecture without explicit developer approval; work one stage (one day from Section 42) at a time; inspect existing files before modifying; never invent external API contracts (always ask the developer to confirm real Agmarknet/weather response shapes against a captured sample); write tests alongside implementation; run tests after every change; report failures plainly, never silently skip/xfail a failing test; maintain backward compatibility with earlier stages' interfaces.

### Reusable STAGE EXECUTION PROMPT

```
You are implementing Stage <N> of the AgriDirect Pricing Engine per
AGRIDIRECT_PRICING_ENGINE_V0.1_SPEC.md, Section <relevant section(s)>.

Before writing code:
1. Re-read the relevant section(s) of the spec exactly as written.
2. List the files you will create or modify, and inspect any existing
   versions of those files first — do not assume their current contents.
3. State any assumption you are about to make explicitly, labeled ASSUMPTION,
   and stop to ask if it materially changes architecture or data contracts.

Implement:
- Only the scope of this stage (see Section 42's table for this day).
- Match existing naming/structure in the repo; do not introduce new
  architectural patterns not present in the spec.

After implementing:
1. Write or update tests for the new code (see Section 31 for relevant test IDs).
2. Run the full test suite, not just new tests.
3. Report: which tests pass/fail, and do not modify or skip a failing test
   to make it pass — report the failure and propose a fix instead.
4. Confirm nothing from a previous stage broke (backward compatibility).

Do not redesign the database schema, API contract, or pricing formulas
defined in the spec without flagging the discrepancy to the developer first.
```

---

# SECTION 44 — GIT STRATEGY

- **Commit frequency**: small, frequent commits per logical unit (e.g., "add MandiPrice model", "add baseline formula + tests") rather than one commit per day.
- **Stage-based commits**: tag the end of each Section-42 day with a commit message prefix `[Day N]` for easy review/rollback.
- **Branch strategy**: single `main` branch is acceptable for a 2-week student team; optionally one `feature/*` branch per Section-42 day merged via fast-forward, to keep review lightweight without full PR overhead.
- **Tags/releases**: tag `v0.1-day3-ingestion`, `v0.1-day9-pricing`, etc. at each major milestone — cheap insurance and clean rollback points for demo day.
- **Rollback points**: always tag right before demo day (`v0.1-demo-ready`) so a last-minute breaking change can be reverted instantly.

---

# SECTION 45 — TECH STACK FINALIZATION

| Component | Technology | V0.1 Required? | Reason |
|---|---|---|---|
| Backend orchestration | Node.js/TS/Express | V0.1 REQUIRED | business logic, auth, existing app dependency |
| Pricing engine | Python/FastAPI | V0.1 REQUIRED | core intelligence, as specified |
| Data handling | Pandas/NumPy | V0.1 REQUIRED | feature engineering, cleaning |
| Forecasting | Prophet | V0.1 REQUIRED | explainable, handles seasonality/missing data well |
| Forecasting | Scikit-learn (HistGradientBoosting) | V0.1 REQUIRED | multivariate nonlinear signal capture |
| Database | PostgreSQL | V0.1 REQUIRED | relational integrity, JSONB for explanations |
| Spatial | PostGIS | V0.1 REQUIRED | nearest-mandi/radius/pooling queries central to the product |
| Cache | Redis | V0.1 REQUIRED | latency for demo-day repeated queries |
| Docker | Docker | OPTIONAL | reproducible demo environment, nice but not blocking |
| MLflow | — | REMOVE FROM V0.1 | DB-based metrics table already suffices |
| OSRM | — | DEFER TO V0.2 | straight-line×multiplier sufficient for prototype logistics |
| OpenStreetMap | — | DEFER TO V0.2 | only needed once OSRM routing is added |
| GitHub Actions | — | DEFER TO V0.2 | manual test runs suffice for 2-week sprint |
| Celery | — | REMOVE FROM V0.1 | a simple cron/scheduled script handles daily ingestion; no task queue volume to justify it |
| Kafka | — | REMOVE FROM V0.1 | no streaming-scale event volume in a single-state prototype |
| XGBoost | — | REMOVE FROM V0.1 | HistGradientBoosting covers the need without an extra dependency |

---

# SECTION 46 — WHAT NOT TO BUILD

- **Deep learning** — REMOVE FROM V0.1: no dataset size or business need justifies it; hurts explainability, a core project value.
- **Kafka / Kubernetes** — REMOVE FROM V0.1: solve problems (streaming scale, multi-service orchestration at scale) this prototype doesn't have.
- **Complex reinforcement learning** for pricing — REMOVE FROM V0.1: unstable, unexplainable, needs far more data/time than available.
- **Nationwide real-time forecasting** — REMOVE FROM V0.1: explicitly out of scope per the prompt; architecture supports future expansion, data does not need to exist yet.
- **Autonomous logistics fleet management** — REMOVE FROM V0.1: a full dispatch/routing/fleet system is its own product; V0.1 only estimates cost and pooling groupings.
- **Production payment settlement** — REMOVE FROM V0.1: Razorpay sandbox simulation only, as already scoped.
- **Advanced computer vision** (e.g., quality grading from photos) — REMOVE FROM V0.1: interesting future differentiator, zero labeled training data available now.
- **Real-time nationwide consumer demand sensing** — NOT AVAILABLE / FUTURE: no such dataset accessible for a hackathon.
- **MSP-based legal pricing guarantees** — REMOVE FROM V0.1: legally sensitive, not verifiable in the available time; use only a data-driven floor (Section 17).

---

# SECTION 47 — SIH TECHNICAL DIFFERENTIATORS

Ranked by technical novelty, feasibility, judge appeal, demo value, real-world impact:

1. **Explainable modular price-range engine** (not a single black-box number) — high feasibility, high judge appeal (directly answers "why should I trust this"), strong real-world impact (farmer trust is the actual adoption blocker).
2. **Confidence-aware fallback hierarchy** that never silently substitutes data — moderate novelty, high feasibility, strong judge appeal for a technical panel, meaningful real-world reliability value.
3. **Spatial pooling via PostGIS** turning fragmented small-farmer supply into truck-capacity-efficient shipments — good novelty for a hackathon context, feasible with existing PostGIS tooling, concrete demo visual (map), directly addresses the stated problem (reducing intermediary logistics margin).
4. **Farmer price floor as a hard constraint, not a UX suggestion** — moderate novelty, high feasibility, strong real-world impact (directly protects the stated beneficiary), demonstrates the team thought about misuse/failure modes, not just the happy path.
5. **Separation of forecasting from price discovery from logistics** — a software-architecture differentiator more than an ML one; scores well on technical rigor with judges who probe design decisions, moderate demo value (shown via the "13-stage" worked example, Section 41).

Do not claim novelty merely from "using AI/ML" — Prophet and gradient boosting on mandi data are well-established techniques; the differentiation is in the **system design around them** (explainability, fallback discipline, farmer protection, spatial pooling), not the algorithms themselves.

---

# SECTION 48 — EXPECTED JUDGE QUESTIONS

| # | Question | Technically correct answer | Evidence/demo |
|---|---|---|---|
| 1 | Why Prophet? | Handles seasonality/missing data natively, interpretable trend decomposition, appropriate for limited per-mandi history | show Prophet component plot |
| 2 | Why not deep learning? | Insufficient data volume, hurts explainability, no demonstrated accuracy gain at this scale | cite Section 46 reasoning |
| 3 | Where does your demand data come from? | AgriDirect's own order/interest activity only — explicitly not third-party consumer demand | show Section 13 disclosure label |
| 4 | How do you handle missing mandi data? | Fallback hierarchy (Section 6), never silent substitution, confidence penalty applied | show a live fallback-triggered response |
| 5 | What happens if Agmarknet goes down? | Ingestion skipped, last-known prices served, confidence degrades via freshness | kill network, show graceful degrade |
| 6 | How do you validate predictions? | Walk-forward temporal validation, per-crop/per-mandi MAE vs baseline threshold | show metrics table |
| 7 | How do you prevent price manipulation? | Server-side computed range from validated data + service-token-only internal API; no client-supplied price accepted as truth | show request/response schema |
| 8 | How do you protect farmers from lowball offers? | Hard price floor (Section 17), blocks/flags below-threshold recommendations | trigger a BLOCKED response live |
| 9 | How do you calculate logistics? | Explicit formula (Section 18), distance × rate + handling + spoilage buffer | show breakdown JSON |
| 10 | How does pooling reduce cost? | Shared shipment cost allocated pro-rata vs each farmer shipping individually | show side-by-side cost comparison |
| 11 | How do you scale? | Config-driven crops/mandis, PostGIS spatial indexing, Pan-India-compatible schema without redesign | show config file adding a new mandi |
| 12 | What happens during sudden crop shortages? | Volatility indicator widens range, caps confidence, arrival-quantity signal reflects shortage | show a low-arrival scenario |
| 13 | How do you explain predictions? | Weighted-contribution driver breakdown, confidence sub-scores, all in explanation payload | show `/price-explanation` |
| 14 | What happens when the model is wrong? | Bounded by acceptance thresholds pre-deployment; rollback via ModelVersion; baseline always available as floor | show rollback mechanism |
| 15 | How is this different from existing mandi price portals? | Portals show historical prices; AgriDirect adds forward-looking fair-price ranges, logistics-aware buyer pricing, and pooling — an actionable transaction layer, not just a lookup | side-by-side comparison |
| 16 | How do you avoid data leakage? | Point-in-time feature computation enforced via `as_of_date`, tested explicitly (T35) | show leakage test |
| 17 | Why a range instead of one number? | Uncertainty is real in agri markets; a single number implies false precision | show spread formula |
| 18 | How do you handle outliers without hiding them? | Flagged + retained + excluded only from training, never deleted | show flagged record in DB |
| 19 | What's your platform fee model and why is it transparent? | Fixed % shown as its own line item, never hidden inside logistics/spread | show Section 21 breakdown |
| 20 | What would change to go from prototype to production? | Real-time IMD/verified weather source, OSRM routing, MLflow/CI, MSP legal verification with domain experts, more mandis/states via existing config-driven schema | reference Sections 34/45/46 DEFER items |

---

# SECTION 49 — TECHNICAL RISK REGISTER

| ID | Risk | Prob. | Impact | Detection | Mitigation | Fallback | Phase |
|---|---|---|---|---|---|---|---|
| R1 | Agmarknet/data.gov.in API changes shape or goes down during demo | Medium | High | ingestion validation errors | schema validation + quarantine, not crash | demo snapshot mode | V0.1 |
| R2 | Insufficient historical data for reliable ML per crop | High | Medium | <90-day check | baseline always available | baseline used, disclosed | V0.1 |
| R3 | Weather API rate limits / unavailability | Medium | Low | ingestion errors | weather features become optional inputs | prediction proceeds without weather term | V0.1 |
| R4 | Node↔FastAPI network issues during live judge demo | Medium | High | circuit breaker trip | retry + circuit breaker + baseline fallback | baseline served, "degraded" flag | V0.1 |
| R5 | Price floor formula blocks too many legitimate recommendations | Low | Medium | monitor BLOCKED rate in logs | tune tolerance config (Section 17) | manual override by developer pre-demo | V0.1 |
| R6 | Team underestimates PostGIS learning curve | Medium | Medium | Day 2 slip | keep spatial queries limited to the 4 documented patterns (Section 3.1) | fall back to plain lat/lon haversine in app code if PostGIS setup fails | V0.1 |
| R7 | Pooling allocation logic produces confusing/incorrect splits | Low | Low | unit test T21 | keep pro-rata allocation simple, documented | disable pooling UI, show individual shipments only | V0.1 |
| R8 | Judges challenge the "illustrative" intermediary-margin numbers (Section 39) | Medium | Medium | — | cite real published sources before demo day if possible | keep "Illustrative" label prominent, cite methodology verbally | V0.1 |
| R9 | Overfitting to the single demo state's data | Medium | Low | held-out test metrics per mandi | per-mandi evaluation (Section 11), not just aggregate | disclose scope honestly (1 state, 5-10 mandis) | V0.1 |
| R10 | Real-time regional production/weather-yield modeling expectation from judges | Low | Low | — | explicitly scope as NOT AVAILABLE/FUTURE, explain why | reference Section 14 limitations | Future |

---

# SECTION 50 — FINAL READINESS CHECKLIST

### Data
- [ ] Ingestion runs successfully against real Agmarknet data for chosen state/mandis
- [ ] Demo snapshot fallback dataset loads and is clearly labeled
- [ ] Data quality pipeline (Section 5) runs without crashing on real ingested data

### ML
- [ ] Baseline, Prophet, and sklearn models all trainable end-to-end
- [ ] At least 3 crops pass the Section 11 acceptance threshold
- [ ] Temporal validation confirmed (no shuffled splits) — T34 passes

### API
- [ ] All Section 25 endpoints return correct schema
- [ ] Error responses match Section 40 format
- [ ] `/health` accurately reflects DB/Redis/model status

### Database
- [ ] Schema matches Section 3 exactly, constraints verified
- [ ] Spatial queries (nearest mandi, radius, pooling) return correct results

### Logistics
- [ ] Cost formula matches hand-calculated worked example (Section 41)
- [ ] Pooling correctly splits/allocates for a multi-farmer scenario

### Frontend
- [ ] Fair price range, confidence, and explanation visible in farmer app
- [ ] Judge dashboard shows confidence breakdown + model status
- [ ] Demo-mode badge appears when in fallback mode

### Security
- [ ] No secrets in source control
- [ ] Internal FastAPI endpoint not publicly reachable
- [ ] Input validation rejects malformed coordinates/quantities

### Performance
- [ ] p95 prediction latency within Section 32 prototype targets during a load test with 10-20 concurrent requests

### Testing
- [ ] All 46 test cases in Section 31 pass (T01–T40 original + T41–T46 remediation)
- [ ] No skipped/xfail tests hiding a real failure

### Failure handling
- [ ] Killing FastAPI mid-demo still returns a usable (degraded) response via Node's circuit breaker
- [ ] Killing Redis does not break correctness, only latency

### Demo
- [ ] Full demo script rehearsed in `DEMO_MODE=true` at least once fully offline
- [ ] "Where did my ₹100 go?" visualization renders with correct labels

### Documentation
- [ ] This spec kept in the repo and referenced by the Section 43 stage prompts
- [ ] README explains how to run ingestion, training, and the demo

---

# INTERNAL CONSISTENCY AUDIT (performed against this document)

- **Architecture**: every module in Section 1's diagram has an owning code directory in Section 35. ✔
- **Data**: every feature in Section 7 has a defined source table from Section 2/3. ✔
- **Formulas**: Sections 8/15/18/20/21/22 all operate consistently in ₹/kg (mandi data stored as ₹/quintal, converted at a single explicit boundary per Section 15.4 — no longer just a flagged assumption, now a documented required utility). ✔
- **Formula double-counting (F1)**: resolved — weather/demand/regional signals enter exactly once, as model regressors feeding `Forecast`; Section 15's `FairPrice` formula now has a single blend term (`w_forecast`). ✔
- **API**: FastAPI request/response models (Section 25) map 1:1 to the Node contract (Section 26) and the JSON examples (Section 40); `confidence` → `reliability` rename applied consistently across Sections 22/23/23.1/26/38. ✔
- **Database**: all foreign keys in Section 3 match entity names in Section 2; API models reference the same field names. (F7, traceability-via-JSON-only, remains an accepted V0.1 limitation — see Remaining Risks below.)
- **ML**: every feature used at inference (Section 7) is computable from data available at prediction time — no feature depends on a future `PriceRecommendation` or `PriceForecast` row.
- **No leakage**: enforced by the single `as_of_date`-threaded feature computation and the temporal splitter (Sections 7, 10), tested explicitly (T35).
- **Fallback consistency**: every external dependency (Agmarknet, weather API, Redis, PostgreSQL, FastAPI) has an explicit fallback in Section 27; the demand-side cold-start fallback (F4, Section 13) now mirrors the same never-silently-substitute discipline as the price-side hierarchy (Section 6).
- **Scope consistency**: nothing marked V0.1 REQUIRED depends on a DEFER/REMOVE/FUTURE item (e.g., pooling doesn't require OSRM; logistics doesn't require Kafka). No new scope was introduced by this remediation pass — only precision fixes to already-in-scope items.
- **Timeline consistency**: Section 42's roadmap (Day 0 + Days 1–14) maps directly onto the module boundaries in Section 35, in dependency order (schema → ingestion → features → models → pricing → logistics → API → integration → frontend → hardening) — achievable by one developer supervising an AI coding agent per the Section 43 workflow.

---

# REMEDIATION CHANGELOG

| Finding | Resolution | Sections Changed |
|---|---|---|
| **F1 (CRITICAL)** — double-counting of weather/demand/regional signal in `FairPrice` | Adopted model-regressors-only architecture: weather/demand/regional-differential enter solely as Prophet/sklearn features (unchanged, Sections 7.3–7.5/14); Section 15's price-discovery formula reduced to a single term, `FairPrice = Baseline + w_forecast·(Forecast − Baseline)`; `w_demand`, `w_weather`, `w_region` removed as separate config weights | 15 (rewritten), 23 (drivers reframed as model-attributed, not independent formula terms), 36 (config weight list updated) |
| **F2** — Section 41 worked example didn't arithmetically reconcile with Section 15 | Recomputed the full worked example by hand, step-by-step, against the corrected Section 15 formula; every intermediate value checked; promoted into a deterministic test fixture `PRICE-E2E-001` with explicit tolerances | 41 (rewritten with 15-step arithmetic trace), 41.1 (new fixture), 31 (T45 added) |
| **F3** — Agmarknet/data.gov.in field names asserted without live verification | Verified via the resource's public documentation and a live-format sample from the "Current Daily Price of Various Commodities from Various Markets (Mandi)" resource; confirmed fields: `state, district, market, commodity, variety, grade, arrival_date, min_price, max_price, modal_price`; `arrival_qty` is **not** present in the verified sample and is downgraded from an implicit-required mapping to OPTIONAL/FUTURE; a first-party, team-executed Day-0 re-verification is still required before Day 3 begins (this remediation confirms the mapping from public documentation, not from the team's own generated API key) | 4 (rewritten), 4.2 (mapping table replaced with verified fields), 42 (Day 0 added) |
| **F4** — Demand Index `norm(x)` divides by zero at cold start (`max == min`) | Explicit rule added: `norm(x) = 0` when `max == min`; when the entire 90-day window has zero history, the Demand Index is excluded from the model's feature set (not zero-forced) and the response is flagged `"dataSource": "insufficient_demand_history"` | 13 (cold-start rule added), 31 (T42 added) |
| **F5** — `ModelAgreement` undefined in baseline-only mode | Explicit default: `ModelAgreement = 0.5` (neutral) when no Prophet/ML comparison exists; disclosed via `"modelAgreementDefault": true` in `fallbacksUsed` and at `/model/status` | 22 (rewritten), 23 (payload field added), 23.1 (API addition), 31 (T43 added) |
| **F6** — "Confidence caps at Medium" ambiguous (range vs. fixed value) | Explicit rule: `PredictionReliability = min(computed_reliability, 79)` — a ceiling, not a fixed override | 22 (rewritten), 31 (T44 added) |
| F10 (related consistency item, folded in alongside F5/F6) | Spec-wide zero-denominator convention stated once and referenced from every ratio-based formula (`volatility_30d`, `ModelAgreement`, etc.) | 22 (convention added), 31 (T46 added) |
| Naming (F5/F6 framing) | "Confidence Score" relabeled **"Prediction Reliability Score"** in judge-facing copy and API field naming (`confidence` → `reliability`), to avoid implying a calibrated statistical probability the hand-tuned weighted sum doesn't provide; internal DB column name may remain `confidence` for schema stability | 22 (renamed), 23 (payload field renamed), 23.1 (API contract note) |

---

# REMAINING RISKS

Only genuinely unresolved items remain listed here; all F1/F2/F3/F5/F6 blockers above are resolved in this document.

1. **F3 still needs first-party confirmation.** This remediation verified the data.gov.in field mapping against public documentation and a third-party-sampled live-format record, not against the team's own generated API key and resource query. The Day 0 action item (Section 42) is a hard prerequisite before Day 3 — if the team's own key/resource returns a different field set (e.g., a state-specific variant), Section 4.2 must be updated again before ingestion coding proceeds.
2. **F7 (traceability, from the original audit) — accepted, not fixed.** `pricing.price_recommendation` still has no `mandi_id` FK or source-row reference columns; traceability to specific `MandiPrice`/`WeatherObservation` rows remains recoverable only via the `explanation`/`fallbacksUsed` JSON, not via SQL joins. This was flagged MEDIUM severity and explicitly out of scope for this remediation pass (which was scoped to F1/F2/F3/F5/F6 only); Section 30's claim should be read as "traceable via the explanation JSON," not "linking...rows" via foreign keys, until a future revision adds the columns.
3. **F8 (data.gov.in key lead time) — mitigated via Day 0, not eliminated.** Real-world approval turnaround for a self-generated API key is outside the team's control; Day 0 reduces but does not remove schedule risk if approval is unusually slow.
4. **F11 (Day 6/7 zero-slack risk) — mitigated via explicit spill allowance, not eliminated.** No calendar day was added; if both Prophet and sklearn implementation slip simultaneously by more than the allowed spill, Day 8's schedule still compresses, which is a real (if now explicitly planned-for) risk.
5. **Illustrative intermediary-margin figures (Section 39, tracked as R8 in the risk register) remain illustrative.** Sourcing real published agricultural-economics figures before demo day is still a to-do, not something this remediation pass could resolve (it requires external citation research, not a spec correction).

---

# IMPLEMENTATION GATE

### 🟢 READY FOR STAGE 0

> The Pricing Engine V0.1 specification is now frozen and ready for stage-by-stage implementation.

All blocking findings (F1 CRITICAL, F2, F3, F5, F6) have been resolved in this document. The remaining items listed under "Remaining Risks" above are schedule/verification risks to actively manage during the sprint (Day 0's live field-mapping check in particular is a hard prerequisite before Day 3), not open specification defects that block Day 1 from starting. Freeze this document (`AGRI-DIRECT-PRICING-ENGINE-V0.1-SPEC-FINAL.md`) alongside the original audit in-repo, per Section 43's instruction that an AI coding agent re-read both before beginning any stage.
