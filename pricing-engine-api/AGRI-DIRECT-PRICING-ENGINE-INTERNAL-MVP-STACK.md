# AGRI-DIRECT PRICING ENGINE — INTERNAL HACKATHON MVP
## Technology Decision

Companion to `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-SCOPE.md`. Every verdict below is justified by the reasoning already given in the Scope document; this file is the single quick-reference table plus exact local setup commands.

Legend: **REQUIRED** · **OPTIONAL** · **DEFER** (to full V0.1) · **REMOVE** (not planned even for V0.1)

---

## 1. Final Stack Table

| Technology | Verdict | Reason (see Scope doc for full detail) |
|---|---|---|
| Python | REQUIRED | Core language for pricing engine, ML, ingestion |
| FastAPI | REQUIRED | Real, versioned, inspectable API — genuine architectural and demo value even without Node.js in front of it |
| Pandas / NumPy | REQUIRED | Feature engineering, cleaning — same as V0.1 |
| Scikit-learn (`HistGradientBoostingRegressor`) | REQUIRED | Sole ML model for MVP — no external compiler/toolchain risk, reuses V0.1's own secondary model as MVP's primary |
| Prophet | DEFER | Stan/cmdstanpy install risk unacceptable in a 3–5 day window on a fresh machine; reintroduced in V0.1 exactly where the parent spec already places it |
| PostgreSQL | REQUIRED | Real relational storage; cheap via Docker; strengthens demo credibility (live query is a trust-building moment) |
| PostGIS | DEFER | Zero measurable benefit at 5–10 mandi scale; plain lat/lon + haversine is numerically equivalent to V0.1's own straight-line×multiplier logistics distance; avoids V0.1's own flagged PostGIS learning-curve risk (R6) |
| Redis | DEFER | No concurrent-load scenario in a single-professor demo session; PostgreSQL latency at this data volume is already imperceptible |
| Streamlit | REQUIRED (frontend) | Fastest reliable path to a full input/chart/explanation dashboard in Python with no separate frontend build |
| React | DEFER | Full V0.1 frontend target; not justified for a single-session internal demo — no styling/component payoff at this scale |
| Node.js | DEFER | Owns auth/rate-limiting/business-workflow in V0.1, none of which exist in a single-operator demo; MVP-ONLY DEVIATION, explicitly flagged, Streamlit calls FastAPI directly |
| Docker | OPTIONAL, recommended Day 1 | Fastest reliable Postgres setup on Windows; not strictly required if the developer already has a local Postgres instance working |

---

## 2. `requirements.txt` (pinned, MVP scope)

```
fastapi==0.115.*
uvicorn[standard]==0.32.*
pydantic==2.9.*
pandas==2.2.*
numpy==2.1.*
scikit-learn==1.5.*
sqlalchemy==2.0.*
psycopg2-binary==2.9.*
python-dotenv==1.0.*
streamlit==1.39.*
requests==2.32.*
plotly==5.24.*
pytest==8.3.*
pytest-cov==5.0.*
```

Notes:
- `plotly` (or Streamlit's own native `st.line_chart`/`st.bar_chart`) covers all three required charts — pin `plotly` only if the native Streamlit charts prove too limited for the forecast-vs-actual overlay; otherwise drop it and use zero extra charting dependencies.
- No `prophet`, no `redis`, no `psycopg2` PostGIS extras, no `geoalchemy2` — all correctly absent per the DEFER decisions above.
- Exact patch versions should be pinned (`==x.y.z`) once `pip freeze` is run after Day 1 setup, to keep the environment reproducible for the remaining days.

---

## 3. Local Development Environment (Windows + Antigravity IDE)

### Prerequisites (assumed already present per the brief)
- Windows 10/11
- Antigravity IDE
- Python 3.11+ (`python --version` to confirm)
- Git (`git --version` to confirm)
- Docker Desktop running (`docker --version` to confirm)

### Setup commands

```powershell
# 1. Clone/initialize repository
git init agridirect-pricing-engine
cd agridirect-pricing-engine

# 2. Python virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Environment variables
copy .env.example .env
# then edit .env: set DATABASE_URL, AGMARKNET_API_KEY (optional — leave blank to force demo-fixture mode), DEMO_MODE=true

# 5. Database setup (Docker)
docker compose up -d postgres
# wait a few seconds for Postgres to accept connections

# 6. Database migrations / schema
python scripts/migrate.py
# (or, if using Alembic: alembic upgrade head)

# 7. Seed config-driven crops/mandis
python scripts/seed_config.py

# 8. Load/verify the demo dataset
python scripts/load_demo_fixture.py

# 9. Train the model (baseline is always available; this trains the sklearn model)
python scripts/train.py --all-crops

# 10. Start the backend
uvicorn app.main:app --reload --port 8000

# 11. In a second terminal (same .venv activated): start the dashboard
streamlit run dashboard/app.py
```

### `.env.example`

```
DATABASE_URL=postgresql://agridirect:agridirect@localhost:5432/agridirect
AGMARKNET_API_KEY=
WEATHER_API_KEY=
DEMO_MODE=true
FASTAPI_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
```

`DEMO_MODE=true` is the safe default for the whole MVP — it forces the demo fixture path regardless of live API availability, which is exactly the behavior wanted for a rehearsed presentation (no risk of a live API call failing mid-demo). Live-mode ingestion (`DEMO_MODE=false`) should only be used for Day 2 development/validation against the real data.gov.in resource, never during the actual presentation.

### `docker-compose.yml` (minimal)

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: agridirect
      POSTGRES_PASSWORD: agridirect
      POSTGRES_DB: agridirect
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

No `redis` service, no PostGIS-enabled Postgres image (`postgis/postgis`) — plain `postgres:16` is sufficient per the Section 1 DEFER decisions.

---

## 4. Path Back to Full V0.1

This table exists so the MVP is never mistaken for a dead end — each DEFER item has a known, additive re-entry point in the frozen parent spec:

| MVP state | V0.1 re-entry point | Nature of the upgrade |
|---|---|---|
| Streamlit calling FastAPI directly | V0.1 §26 | Insert Node.js between frontend and FastAPI; FastAPI's internals unchanged |
| Plain lat/lon + haversine | V0.1 §3 DDL, §3.1 | Migrate columns to `geography(Point,4326)`, add GIST indexes; distance semantics already equivalent |
| No Redis | V0.1 §24 | Add cache-aside reads/writes around existing DB queries; no query logic changes |
| sklearn-only forecasting | V0.1 §9, §12 | Add Prophet as a second trained model; extend model-selection logic to compare both |
| 3-component reliability score | V0.1 §22 | Add `ModelAgreement`, `MandiAvailability`, `WeatherAvailability` terms once a second model and full fallback hierarchy exist |
| Single vehicle class, no pooling | V0.1 §18–20 | Add vehicle-class selection table and pooling algorithm; cost formula structure unchanged |
| Text explanation panel | V0.1 §23 | Formalize into the full JSON schema; same underlying signals, richer structure |

No MVP-stage code needs to be deleted or rewritten to make any of these upgrades — every deferred item is additive.
