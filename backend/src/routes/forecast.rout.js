import { Router } from "express";
import { verifyJWT } from "../middlewares/auth.middleware.js";
import { getForecast, checkForecasterHealth } from "../controllers/forecast.controller.js";

const router = Router();

// All forecast routes require authentication
// Both farmers and consumers can access forecasts

// Generate 7-day price forecast
router.route("/predict").post(verifyJWT, getForecast);

// Optional: Internal health check for forecaster connectivity
router.route("/health").get(verifyJWT, checkForecasterHealth);

export default router;