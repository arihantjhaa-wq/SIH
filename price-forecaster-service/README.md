# AgriDirect Price Forecaster Service

7-day crop price forecasting microservice using weather data, historical market records, and Random Forest regression.

## Architecture

```
POST /api/v1/forecast/predict
    ↓
Location geocoding (Google Maps → Nominatim fallback)
    ↓
Weather data (Open-Meteo 30-day historical + 7-day forecast)
    ↓
Local dataset query (India agricultural prices)
    ↓
Random Forest training
    ↓
7-day price forecast + trend analysis
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and add your Google Maps API key (optional, Nominatim fallback available):

```env
GOOGLE_MAPS_API_KEY=AIzaSy...
PORT=8002
```

### 3. Run Locally

```bash
python main.py
```

Service starts at `http://localhost:8002`

## API Documentation

Once running:
- Swagger UI: `http://localhost:8002/api/v1/docs`
- ReDoc: `http://localhost:8002/api/v1/redoc`

## Endpoints

### Health Check

```bash
GET /api/v1/health
```

Returns service status and timestamp.

### Generate Forecast

```bash
POST /api/v1/forecast/predict
```

Request body:

```json
{
  "location": "Kolkata",
  "state": "West Bengal",
  "commodity": "Tomato"
}
```

Response:

```json
{
  "commodity": "Tomato",
  "state": "West Bengal",
  "location": "Kolkata",
  "resolved_location": {
    "address": "Kolkata, West Bengal, India",
    "latitude": 22.5726,
    "longitude": 88.3639,
    "source": "google_maps"
  },
  "forecast": [
    {
      "date": "2026-09-09",
      "predicted_price_inr_per_kg": 123.45,
      "rainfall_mm": 4.2,
      "temperature_c": 31.5
    }
  ],
  "trend": {
    "direction": "rising",
    "change_percent": 4.8,
    "first_price_inr": 118.2,
    "last_price_inr": 124.7
  },
  "data_source": "model",
  "timestamp": "2026-09-09T11:39:36.988Z"
}
```

## Key Features

### Deterministic Fallback

When historical data is insufficient:
- **No random noise** — uses deterministic formula: `price = BASE + rainfall × COEFFICIENT`
- **Transparent source** — `data_source` field indicates "fallback" vs "model"

### Trend Calculation

```
percent_change = ((last_price - first_price) / first_price) × 100

Thresholds:
  > +1%   → "rising"
  < -1%   → "falling"
  ±1%     → "stable"
```

### Multi-Source Geocoding

1. **Google Maps** (with API key)
2. **Nominatim/OpenStreetMap** (fallback, India-restricted)

## Deployment to Render

### Create Web Service

1. New **Web Service** on Render
2. Connect GitHub repository
3. Configure:

```
Name:                price-forecaster-service
Environment:         Python
Build Command:       pip install -r requirements.txt
Start Command:       uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables (Render)

Set in Render dashboard:

```
GOOGLE_MAPS_API_KEY      (your key, optional)
DATASET_FILE             india_agricultural_prices_last_5_days_june_september_2026.json
PORT                     $PORT (auto-set by Render)
```

### Service Health

Service responds to `GET /api/v1/health` with:

```json
{
  "status": "ok",
  "service": "price-forecaster-service",
  "timestamp": "...",
  "forecast_days": 7,
  "timezone": "Asia/Kolkata"
}
```

## Integration with Marketplace Backend

The marketplace backend acts as a proxy:

1. React frontend → POST `/api/v1/forecast/predict`
2. Backend validates authentication
3. Backend forwards to forecaster service
4. Backend returns clean response

**Never call forecaster directly from the frontend.**

## Error Handling

| HTTP Code | Description |
|-----------|-------------|
| 401       | Authentication required (handled by backend proxy) |
| 422       | Invalid location or parameters |
| 503       | Weather service unavailable |
| 500       | Internal service error |

All errors return user-friendly messages, never stack traces.

## Testing

### Manual Test

```bash
curl -X POST "http://localhost:8002/api/v1/forecast/predict" \
  -H "Content-Type: application/json" \
  -d '{"location": "Kolkata", "state": "West Bengal", "commodity": "Tomato"}'
```

### Automated Tests

```bash
# TODO: Add pytest suite
pytest tests/
```

## Data Sources

1. **Weather**: Open-Meteo (free, no API key)
2. **Geocoding**: Google Maps (with key) or Nominatim (fallback)
3. **Market Data**: `india_agricultural_prices_last_5_days_june_september_2026.json` (local file)

## Security Notes

- API keys stored in environment variables only
- CORS configured for marketplace backend origins only
- Input validation on all endpoints
- No secrets exposed in responses
- Rate limiting is the responsibility of the backend proxy

## Monitoring

Monitor these endpoints:
- `GET /api/v1/health` — service health
- Response times in logs
- Error rates via Render metrics
