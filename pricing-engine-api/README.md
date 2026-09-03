# AgriDirect Pricing Engine

Explainable AI pricing engine for AgriDirect that combines mandi market data, demand, weather, forecasting, and logistics signals to generate transparent and confidence-aware agricultural price recommendations.

---

## 📋 Project Overview

The AgriDirect Pricing Engine is an MVP (Minimum Viable Product) pricing system for agricultural commodities in India. It computes a **fair farmer payout price** and **final buyer price** by combining:

1. **Market Data Ingestion** — AGMARKNET mandi prices with automated fallback to synthetic demo fixtures
2. **Feature Engineering** — Lag features, rolling means, price momentum, 30-day volatility, demand index
3. **Forecasting** — sklearn `HistGradientBoostingRegressor` with walk-forward temporal validation
4. **Price Discovery** — Baseline + ML forecast blend, volatility-aware spread, farmer protection floor
5. **Reliability Scoring** — 7-subscore model (data freshness, historical volume, validation quality, mandi availability, weather, model agreement, market volatility)
6. **Logistics** — Haversine distance + road factor, vehicle class selection, transport/handling/spoilage costs
7. **End-to-End Integration** — Farmer payout + logistics + platform fee = buyer price (invariant enforced)
8. **REST API** — FastAPI with Pydantic v2 validation, structured errors, OpenAPI docs

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (optional — runs in `DEMO_MODE` without DB)
- Virtual environment tool (`venv` or `conda`)

### Installation

```bash
# Clone and enter project
cd Agridirect-pricing-engine

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env if needed (defaults work for DEMO_MODE)
```

### Running the API

```bash
# Start API server (with DEMO_MODE=true, no PostgreSQL needed)
.venv\Scripts\uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

### Running Tests

```bash
# Full test suite (all stages)
.venv\Scripts\python -m pytest -v

# Specific stage
.venv\Scripts\python -m pytest tests/test_stage10.py -v

# With coverage
.venv\Scripts\python -m pytest --cov=app --cov-report=term-missing
```

### Data Ingestion (Demo Mode)

```bash
# Demo fixtures are loaded automatically in DEMO_MODE
# To manually trigger demo data loading:
.venv\Scripts\python -c "
from app.data.ingest import ingest_market_prices
ingest_market_prices()
print('Demo data loaded')
"
```

### Model Training

```bash
# Train sklearn models for all 20 crops (requires PostgreSQL with demo data)
.venv\Scripts\python -m app.forecasting.sklearn_model --commodity tomato --mandi pune
# Or use the training script
.venv\Scripts\python scripts/train_models.py
```

> **Note**: Model training requires PostgreSQL. In `DEMO_MODE=true`, the engine runs in **baseline-only mode** (no ML forecasts) — full results still returned with `ml_available: false`.

---

## 🏗 Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        API LAYER (Stage 9)                      │
│  FastAPI / Pydantic v2                                          │
│  POST /api/v1/pricing/estimate   GET /health                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   INTEGRATION LAYER (Stage 8)                   │
│  compute_end_to_end_price()                                     │
│  - Validates pricing + logistics results                        │
│  - Enforces: buyer = farmer + logistics + platform              │
│  - Builds complete explanation payload                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ PRICING (6)   │    │ LOGISTICS (7) │    │ EXPLANATION   │
│ predict_price │    │ estimate_log  │    │ (integrated)  │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────────┐
│                    FORECASTING (Stage 4)                     │
│  forecast_price() → baseline + ML (HistGradientBoosting)    │
└────────────────────────────┬─────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │ FEATURES (3)    │
                    │ lag, rolling,   │
                    │ volatility,     │
                    │ demand_index    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ DATA INGEST (2) │
                    │ AGMARKNET API   │
                    │ CSV fallback    │
                    └─────────────────┘
```

### Key Invariants (Never Modified)

| Invariant | Formula | Stage |
|-----------|---------|-------|
| **Price Decomposition** | `buyer_price = farmer_payout + logistics + platform_fee` | 8 |
| **Farmer Floor** | `FLOOR = 0.85 × Baseline`; `BLOCKED if FairPrice.Lower < FLOOR` | 6 |
| **Reliability** | `100 × [0.35·Freshness + 0.30·Volume + 0.35·Quality]` | 6 |
| **Fair Price** | `Baseline + w_forecast × (ML - Baseline)` (baseline-only = Baseline) | 6 |
| **Demand Index** | `norm(x) = 0` when `max == min` (cold-start fix) | 3 |

---

## 📁 Project Structure

```
Agridirect-pricing-engine/
├── app/
│   ├── api/
│   │   ├── main.py              # FastAPI app + exception handlers
│   │   ├── routes/pricing.py    # POST /estimate endpoint
│   │   └── schemas/pricing.py   # Pydantic request/response models
│   ├── core/db.py               # SQLAlchemy session management
│   ├── data/
│   │   ├── ingest.py            # AGMARKNET client + CSV fallback
│   │   └── quality.py           # Price validation/cleaning
│   ├── features/
│   │   ├── engineering.py       # Lag, rolling, momentum, volatility
│   │   ├── demand.py            # Demand Index with cold-start fix
│   │   └── weather.py           # Weather feature extraction
│   ├── forecasting/
│   │   ├── baseline.py          # Weighted moving average
│   │   └── sklearn_model.py     # HistGradientBoosting + walk-forward
│   ├── logistics/
│   │   ├── distance.py          # Haversine + road factor
│   │   ├── cost.py              # Transport/handling/spoilage
│   │   ├── validate.py          # Input validation
│   │   └── engine.py            # estimate_logistics()
│   ├── pricing/
│   │   ├── discovery.py         # Fair price, spread, range
│   │   ├── farmer_floor.py      # 0.85× baseline floor
│   │   ├── reliability.py       # 7-subscore reliability
│   │   ├── explain.py           # Explanation builder
│   │   ├── engine.py            # predict_price() orchestrator
│   │   └── integration.py       # compute_end_to_end_price()
│   └── schemas/                 # (merged into api/schemas)
├── configs/
│   ├── crops.yaml               # 20 demo crops + metadata
│   ├── mandis.yaml              # 7 Maharashtra mandis + coords
│   └── logistics.yaml           # Vehicle classes, rates, handling
├── data/
│   └── demo/                    # Synthetic CSV fixtures
│       ├── mandi_prices.csv     # 19,605 records, 140 days
│       └── weather.csv          # 980 records
├── models/                      # Trained model artifacts (.pkl)
├── scripts/
│   └── train_models.py          # Batch training script
├── tests/
│   ├── test_stage2.py           # DB, ingestion, demo fixtures
│   ├── test_stage3.py           # Features, baseline, demand index
│   ├── test_stage4.py           # Forecasting, walk-forward, MAE
│   ├── test_stage6.py           # Pricing (38 tests)
│   ├── test_stage7.py           # Logistics (71 tests)
│   ├── test_stage8.py           # Integration (38 tests)
│   ├── test_stage9.py           # API layer (39 tests)
│   └── test_stage10.py          # Hardening (44 tests)
├── docs/
│   └── demo-data-provenance.md  # Synthetic data documentation
├── .env.example                 # Environment template
├── requirements.txt
└── README.md
```

---

## 🧪 Test Suite Summary

| Stage | Tests | Coverage |
|-------|-------|----------|
| Stage 2 | 4 | DB schema, config seeding, ingestion, demo fallback |
| Stage 3 | 12 | Features, baseline WMA, demand index cold-start |
| Stage 4 | 15 | Temporal split, training, MAE, baseline fallback |
| Stage 6 | 38 | Fair price, spread, floor, reliability, explanation |
| Stage 7 | 71 | Distance, vehicle class, costs, pooling, spoilage |
| Stage 8 | 38 | End-to-end, invariants, explanations, regression |
| Stage 9 | 39 | API endpoints, validation, errors, OpenAPI |
| Stage 10 | 44 | Large qty, API failure, baseline-only, stale data, config crops, determinism, high-value, explanations |
| **Total** | **261** | **Full pipeline + API** |

> **Note**: Stage 2 & 4 tests that require PostgreSQL fail locally (expected — no local DB). All other 225 tests pass.

---

## 🌐 API Reference

### POST /api/v1/pricing/estimate

Calculate pricing estimate for a commodity shipment.

**Request Body:**
```json
{
  "commodity": "Tomato",
  "quantity_kg": 500.0,
  "farmer_location": {"lat": 18.5204, "lon": 73.8567},
  "buyer_location": {"lat": 19.0760, "lon": 72.8777},
  "farmer_declared_minimum": 19.0,
  "platform_fee_pct": 0.05
}
```

**Response (key fields):**
```json
{
  "commodity_id": "112fcfa1-8c94-52ae-91a6-abb7dc6ec8b5",
  "mandi_id": "97ce83b2-322f-5c5c-8fce-22f2eacdd677",
  "as_of_date": "2026-09-01",
  
  "baseline_price_per_kg": 20.16,
  "fair_price_per_kg": 20.16,
  "farmer_payout_per_kg": 20.16,
  
  "price_range_low": 17.90,
  "price_range_high": 22.42,
  "reliability_score": 45,
  
  "protected_floor": 17.14,
  "floor_blocked": false,
  
  "distance_km": 118.48,
  "vehicle_class": "tempo",
  "logistics_cost_per_kg": 1.75,
  
  "platform_fee_pct": 0.05,
  "platform_fee_per_kg": 1.01,
  
  "buyer_price_per_kg": 22.92,
  "buyer_total": 11460.00,
  "farmer_total": 10080.00,
  "logistics_total": 876.00,
  "platform_total": 504.00,
  
  "is_fallback": false,
  "explanation": { ... }
}
```

**Error Responses:**
- `400` — Invalid commodity, insufficient data, validation error
- `422` — Request body validation failed (Pydantic)
- `500` — Internal server error (no stack trace exposed)

### GET /health

```json
{"status": "ok"}
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://agridirect:agridirect@localhost:5432/agridirect` | PostgreSQL connection |
| `DEMO_MODE` | `true` | Use synthetic fixtures instead of live API |
| `AGMARKNET_API_KEY` | `` | Live API key (optional) |
| `WEATHER_API_KEY` | `` | Weather API key (optional) |
| `FASTAPI_BASE_URL` | `http://localhost:8000` | API base URL |
| `LOG_LEVEL` | `INFO` | Logging level |

### Crop Configuration (`configs/crops.yaml`)

20 demo crops configured (Tomato, Onion, Potato, Rice, Wheat, Maize, Groundnut, Soybean, Mustard, Gram, Lentil, Pigeon Pea, Cabbage, Cauliflower, Green Chilli, Brinjal, Mango, Banana, Orange, Apple). Add additional crops by editing YAML — **no code changes required**.

### Mandi Configuration (`configs/mandis.yaml`)

7 Maharashtra mandis with GPS coordinates. API auto-selects nearest mandi to farmer location.

### Logistics Configuration (`configs/logistics.yaml`)

- 4 vehicle classes (auto_rickshaw 200kg → truck 5000kg)
- Handling: ₹30/load + ₹30/unload
- Spoilage buffer: ₹0.50/kg (max 5%)
- Road factor: 1.3× straight-line distance

---

## 🔒 Deferred Items (Post-MVP)

| Feature | Status | Notes |
|---------|--------|-------|
| PostgreSQL production setup | Deferred | Stage 11+ |
| Redis caching | Deferred | Stage 11+ |
| Authentication / RBAC | Deferred | Stage 11+ |
| React / Flutter dashboard | Deferred | Stage 11+ |
| Docker / Kubernetes | Deferred | Stage 11+ |
| CI/CD pipelines | Deferred | Stage 11+ |
| Pooling / multi-farmer logistics | Deferred | Config has `pooling.enabled: false` |
| Prophet / XGBoost alternatives | Deferred | sklearn HistGradientBoosting only |
| Multi-state mandi expansion | Deferred | Maharashtra only for MVP |

---

## 📄 Documentation

- **Demo Data Provenance**: `docs/demo-data-provenance.md` — methodology for synthetic CSV fixtures
- **API Docs**: `/docs` (Swagger UI) or `/redoc` (ReDoc) when server running

---

## 📜 License

Internal Hackathon MVP — AgriDirect 2026

---

## 🤝 Contributing

This is an internal hackathon project. For questions or issues, contact the AgriDirect team.