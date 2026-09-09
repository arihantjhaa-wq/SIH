import { verifyJWT } from "../middlewares/auth.middleware.js";
import { asyncHandler } from "../utils/async-handler.js";
import { ApiError } from "../utils/api-error.js";
import {
  callForecastService,
  validateForecastRequest,
} from "../utils/forecast.js";

// ==============================================================================
// Forecast Controller
// ==============================================================================

/**
 * POST /api/v1/forecast/predict
 *
 * Generate a 7-day price forecast.
 *
 * Request body:
 *   { location, state, commodity }
 *
 * Response:
 *   { commodity, state, location, resolved_location, forecast[], trend, data_source, timestamp }
 */
export const getForecast = asyncHandler(async (req, res) => {
  // Authentication is handled by middleware (verifyJWT)
  // Both farmers and consumers can access forecasts

  const { state, commodity } = req.body;

  // Validate request
  const validated = validateForecastRequest(commodity, state);

  // Call forecaster service
  const forecast = await callForecastService({
    state: validated.state,
    commodity: validated.commodity,
  });

  // Return clean response
  res.status(200).json({
    success: true,
    data: forecast,
  });
});

// ==============================================================================
// Health check for forecaster (internal use)
// ==============================================================================

export const checkForecasterHealth = asyncHandler(async (req, res) => {
  const PRICE_FORECASTER_URL =
    process.env.PRICE_FORECASTER_SERVICE_URL || "http://localhost:8002";

  try {
    const response = await fetch(`${PRICE_FORECASTER_URL}/api/v1/health`, {
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      const health = await response.json();
      res.status(200).json({
        success: true,
        status: "connected",
        forecaster: health,
      });
    } else {
      res.status(502).json({
        success: false,
        status: "unhealthy",
        message: "Forecaster returned non-200 status",
      });
    }
  } catch (err) {
    res.status(502).json({
      success: false,
      status: "unreachable",
      message: err.message || "Could not connect to forecaster",
    });
  }
});