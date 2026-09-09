# AgriDirect Price Forecaster — Deployment Guide

Complete deployment guide for the new Price Forecaster Service and integration with existing AgriDirect system.

## Architecture Overview

```
Vercel Frontend (React)              → Vercel Project
    ↓
Render Backend (Express.js)           → Render Web Service (Node.js)
    ↓
Render Price Forecaster (FastAPI)     → NEW Render Web Service (Python 3.11)
    ↓
External APIs (Open-Meteo, Google Maps)
    ↓
Local Dataset (JSON file in service)
```

## New Service: Price Forecaster

### Render Configuration

**Create new Web Service:**

| Setting | Value |
|---------|-------|
| Name | `price-forecaster-service` |
| Environment | `Python` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/v1/health` |
| Plan | Starter (free) |

**Environment Variables (Render):**

```
GOOGLE_MAPS_API_KEY=AIzaSy... (your Google Maps API key, optional)
PORT=$PORT (auto-set by Render)
DATASET_FILE=india_agricultural_prices_last_5_days_june_september_2026.json
TIMEZONE=Asia/Kolkata
```

**Key Points:**

- Port uses `$PORT` (Render's internal port)
- Google Maps API key is optional (fallback to Nominatim available)
- Dataset file included in repository (67MB JSON)
- Service URL will be: `https://price-forecaster-service.onrender.com`

### Health Check

Service responds to: `GET /api/v1/health`

```json
{
  "status": "ok",
  "service": "price-forecaster-service",
  "timestamp": "...",
  "forecast_days": 7,
  "timezone": "Asia/Kolkata"
}
```

## Update Existing Marketplace Backend

### Environment Variables (Backend .env)

Update Render's environment variables for the existing backend service:

```
# Add this new variable
PRICE_FORECASTER_SERVICE_URL=https://price-forecaster-service.onrender.com

# Update CORS to include Vercel domain
CORS_ORIGIN=https://your-frontend.vercel.app,http://localhost:5173
```

**Note:** Keep the existing variables (MONGODB_URI, JWT secrets, etc.)

### Backend Routes Added

New routes in the marketplace backend:

```
POST /api/v1/forecast/predict
GET  /api/v1/forecast/health (internal)
```

## Frontend (Vercel)

### Environment Variables (Vercel)

Frontend already has:
```
VITE_API_BASE_URL=https://<your-backend>.onrender.com
```

**No new variables needed** — all forecasting goes through backend proxy.

### Updated Navigation

Frontend now includes:
1. **Farmer Portal**: AI Market Pricing Advisor widget
2. **Product Detail Page**: 7-Day Price & Weather Trend section  
3. **Market Insights**: Full forecast dashboard (add to navbar)

## Dependencies

### Price Forecaster Service
```
requirements.txt includes:
- fastapi, uvicorn
- pandas, scikit-learn
- requests
- pydantic, pydantic-settings
```

### Frontend
```
package.json additions:
- recharts (charting library)
- No other new dependencies
```

## Testing Checklist Before Deployment

### Price Forecaster Service (Local)
```bash
cd price-forecaster-service
pip install -r requirements.txt
python main.py
```

Test with:
```bash
curl -X POST "http://localhost:8002/api/v1/forecast/predict" \
  -H "Content-Type: application/json" \
  -d '{"location": "Kolkata", "state": "West Bengal", "commodity": "Tomato"}'
```

### Backend Integration (Local)
```bash
cd backend
npm install
npm run dev
```

Test proxy route:
```bash
curl -X POST "http://localhost:7200/api/v1/forecast/predict" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{"location": "Kolkata", "state": "West Bengal", "commodity": "Tomato"}'
```

### Frontend (Local)
```bash
cd frontend
npm install
npm run dev
```

Verify:
1. Farmer Portal shows forecast widget
2. Product detail page includes 7-day chart
3. Market Insights page works

## Deployment Sequence

### 1. Deploy Price Forecaster Service

1. Push code to GitHub (ensure all files in `price-forecaster-service/` are included)
2. On Render → New Web Service
3. Connect to repository
4. Configure as above
5. Wait for service to deploy and become healthy

### 2. Update Backend Configuration

1. Get the deployed forecaster URL from Render
2. Add `PRICE_FORECASTER_SERVICE_URL` to backend's Render environment variables
3. Deploy backend (or environment changes will trigger automatic deployment)
4. Verify backend can connect to forecaster:
   ```
   GET https://<backend>.onrender.com/api/v1/forecast/health
   ```

### 3. Deploy Frontend

1. Push frontend changes
2. Vercel will auto-deploy
3. Verify frontend connects to backend correctly

## Monitoring & Troubleshooting

### Logs to Check

**Price Forecaster (Render logs):**
- Errors with Google Maps API key
- Open-Meteo API failures
- Dataset loading errors
- Model training times

**Marketplace Backend (Render logs):**
- Authentication failures on forecast routes
- Timeouts connecting to forecaster (30s timeout)
- Validation errors

### Common Issues

| Issue | Solution |
|-------|----------|
| Forecaster times out (>30s) | Reduce historical days in config or optimize model |
| Google Maps API rate limit | Use Nominatim fallback (no key needed) |
| CORS errors | Verify CORS_ORIGIN includes Vercel domain |
| Frontend can't access forecast | Verify JWT token is being sent |

## Rollback Plan

If forecast service fails:

1. **Immediate**: Disable forecast widget in frontend (could hide via feature flag)
2. **Short-term**: Update backend to return fallback/placeholder data
3. **Long-term**: Fix forecaster issues and redeploy

## Cost Implications

### Free Tier (Starter)

**Render:**
- Price Forecaster Service: Free (512 MB RAM, 0.1 CPU)
- Marketplace Backend: Already deployed
- **Total Services:** 2 web services (within free limits)

**Vercel:**
- Frontend: Already deployed

**External APIs:**
- Open-Meteo: Free
- Google Maps: Free tier (up to $200/month credits)
- Nominatim: Free

## Security Notes

1. **Google Maps API key**: Only stored in Render environment variables, never exposed to frontend
2. **Dataset**: Contains public market data only, no PII
3. **Authentication**: Forecast routes protected by existing JWT system
4. **CORS**: Configured for backend-origin only, no direct browser→forecaster calls
5. **Input validation**: All user input validated on backend

## Performance Metrics

### Expected Response Times

| Component | Time |
|-----------|------|
| Frontend UI render | 50-100ms |
| Backend proxy | 1-5ms |
| Forecaster geocoding | 200-500ms |
| Forecaster weather fetch | 100-300ms |
| Forecaster model prediction | 50-200ms |
| **Total** | **~800-1200ms** |

### Monitoring Metrics
- Response time < 2s (95th percentile)
- Error rate < 1%
- Uptime > 99%

## Maintenance Tasks

### Weekly
  - Check service health metrics
  - Verify external API limits not exceeded

### Monthly  
  - Consider updating historical dataset if available
  - Review forecast accuracy (if feedback collected)

### As Needed
  - Update dependencies in requirements.txt
  - Tune Random Forest hyperparameters
  - Add new commodities/states to dataset

## Contact Points

- **Service Owner**: AgriDirect Team
- **Infrastructure**: Render dashboard
- **Frontend**: Vercel dashboard
- **Dataset Source**: Ministry of Agriculture public data

---

## Final Verification Checklist

- [ ] Price Forecaster Service deployed to Render and healthy
- [ ] Backend PRICE_FORECASTER_SERVICE_URL environment variable set
- [ ] Backend forecast routes responding correctly
- [ ] Frontend deployed to Vercel
- [ ] Farmer Portal widget appears and works
- [ ] Product detail page includes forecast section
- [ ] Market Insights page accessible
- [ ] No console errors in browser
- [ ] All three user workflows tested
