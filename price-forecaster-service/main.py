"""
AgriDirect Price Forecaster Service — FastAPI

7-day crop price forecasting using weather, historical market data, and Random Forest.

Endpoints:
  GET  /api/v1/health             — Health check
  POST /api/v1/forecast/predict   — Generate 7-day forecast

Architecture:
  Location → Geocode (Google/Nominatim)
  → Fetch weather (Open-Meteo)
  → Query dataset (local JSON)
  → Train Random Forest
  → Predict 7 days
  → Return JSON
"""

import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config import settings
from models import ForecastRequest, ForecastResponse, ResolvedLocation
from services.location_service import LocationService, LocationError
from services.weather_service import WeatherService, WeatherError
from services.dataset_service import get_dataset_service
from services.forecast_service import ForecastService, ForecastError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AgriDirect Price Forecaster Service",
    description="7-day crop price forecasting using weather + historical data",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc"
)

# CORS — allow requests from Marketplace Backend (port 7200)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Marketplace backend is internal; allow for dev
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)


# ==============================================================================
# Health check
# ==============================================================================
@app.get("/")
async def root():
    return {
        "service": "AgriDirect Price Forecaster",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "service": "price-forecaster-service",
        "timestamp": datetime.now().isoformat(),
        "forecast_days": settings.FORECAST_DAYS,
        "timezone": settings.TIMEZONE
    }


# ==============================================================================
# Main forecast endpoint
# ==============================================================================
@app.post("/api/v1/forecast/predict", response_model=ForecastResponse)
async def predict_forecast(request: ForecastRequest):
    """
    Generate a 7-day price forecast.

    Request:
        {
            "location": "Kolkata",
            "state": "West Bengal",
            "commodity": "Tomato"
        }

    Response:
        {
            "commodity": "Tomato",
            "state": "West Bengal",
            "location": "Kolkata",
            "resolved_location": {...},
            "forecast": [...],
            "trend": {...},
            "data_source": "model",
            "timestamp": "2026-09-09T11:39:36.988Z"
        }
    """
    start_time = datetime.now()
    logger.info(f"Forecast request: state={request.state}, commodity={request.commodity}")

    try:
        # -----------------------------------------------------------------
        # 1. Fetch weather data (historical + forecast)
        # We use the state's capital city for weather data lookup
        # -----------------------------------------------------------------
        # Use state-based default coordinates (approximated from major agricultural centers)
        # This avoids requiring an exact district-level location
        state_coords = {
            "West Bengal": (22.5726, 88.3639),   # Kolkata
            "Maharashtra": (19.076, 72.8777),    # Mumbai
            "Karnataka": (12.9716, 77.5946),    # Bangalore
            "Telangana": (17.385, 78.4867),     # Hyderabad
            "Tamil Nadu": (13.0827, 80.2707),   # Chennai
            "Andhra Pradesh": (16.5062, 80.6483), # Vijayawada
            "Gujarat": (23.0225, 72.5714),      # Ahmedabad
            "Rajasthan": (26.9124, 75.7873),    # Jaipur
            "Uttar Pradesh": (26.8467, 80.9462), # Lucknow
            "Madhya Pradesh": (23.2599, 77.4126), # Bhopal
            "Kerala": (8.5241, 76.9366),        # Thiruvananthapuram
            "Punjab": (30.7333, 76.7794),       # Chandigarh
            "Haryana": (29.0588, 76.8566),      # Chandigarh
            "Odisha": (20.2961, 85.8245),       # Bhubaneswar
            "Assam": (26.2006, 92.9376),         # Guwahati
            "Bihar": (25.5941, 85.1376),         # Patna
            "Jharkhand": (23.3441, 85.3096),     # Ranchi
            "Chhattisgarh": (21.2514, 81.6296), # Raipur
            "Tripura": (23.8315, 91.2825),      # Agartala
            "Meghalaya": (25.5744, 91.8823),    # Shillong
        }
        lat, lon = state_coords.get(request.state, (22.5726, 88.3639))
        full_address = f"{request.state}, India"
        geocode_source = "state_default"

        try:
            hist_weather_df, forecast_weather_df = WeatherService.fetch_weather(
                latitude=lat,
                longitude=lon,
                days_historical=settings.HISTORICAL_DAYS
            )
        except WeatherError as e:
            logger.error(f"Weather fetch failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Weather data is currently unavailable."
            )

        # -----------------------------------------------------------------
        # 3. Load historical price data for this commodity/state
        # -----------------------------------------------------------------
        dataset_service = get_dataset_service(settings.DATASET_FILE)
        historical_prices_df = dataset_service.get_historical_prices(
            state=request.state,
            commodity=request.commodity
        )

        # -----------------------------------------------------------------
        # 4. Train model and generate forecast
        # -----------------------------------------------------------------
        try:
            result = ForecastService.generate_forecast(
                historical_prices=historical_prices_df,
                historical_weather=hist_weather_df,
                forecast_weather=forecast_weather_df,
                commodity=request.commodity,
                state=request.state
            )
        except ForecastError as e:
            logger.error(f"Forecast generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Forecast generation failed."
            )

        # -----------------------------------------------------------------
        # 5. Build final response (no location needed for commodity/state-only forecasting)
        # -----------------------------------------------------------------
        elapsed_ms = round((datetime.now() - start_time).total_seconds() * 1000, 2)
        logger.info(f"Forecast completed in {elapsed_ms}ms")

        return ForecastResponse(
            commodity=request.commodity,
            state=request.state,
            forecast=result["forecast"],
            trend=result["trend"],
            data_source=result["data_source"],
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        logger.exception("Unexpected error in forecast endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )


# ==============================================================================
# Exception handlers
# ==============================================================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


# ==============================================================================
# Entry point
# ==============================================================================
if __name__ == "__main__":
    logger.info(f"Starting Price Forecaster Service on port {settings.PORT}")
    logger.info(f"Using dataset: {settings.DATASET_FILE}")
    logger.info(f"Google Maps key configured: {bool(settings.GOOGLE_MAPS_API_KEY)}")
    logger.info(f"Timezone: {settings.TIMEZONE}")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
