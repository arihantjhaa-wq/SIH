import { ApiError } from "../utils/api-error.js";

const PRICE_FORECASTER_URL =
  process.env.PRICE_FORECASTER_SERVICE_URL || "http://localhost:8002";

const FORECASTER_TIMEOUT_MS = 30000; // 30 seconds

export async function callForecastService({
  commodity,
  state,
}) {
  let response;
  try {
    response = await fetch(`${PRICE_FORECASTER_URL}/api/v1/forecast/predict`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        commodity,
        state,
      }),
      signal: AbortSignal.timeout(FORECASTER_TIMEOUT_MS),
    });
  } catch (err) {
    console.error("[FORECAST] Network error calling forecaster:", err?.message);
    throw new ApiError(
      502,
      "Market forecast service is temporarily unavailable. Please try again in a moment."
    );
  }

  const json = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = json?.detail || json?.message || `HTTP ${response.status}`;
    console.error(`[FORECAST] Forecaster returned ${response.status}:`, detail);

    if (response.status === 422) {
      throw new ApiError(422, detail);
    }

    if (response.status === 503) {
      throw new ApiError(
        503,
        "Weather data is temporarily unavailable. Please try again shortly."
      );
    }

    throw new ApiError(
      502,
      "Could not generate forecast. Please try again."
    );
  }

  return json;
}

export function validateForecastRequest(commodity, state) {
  const errors = [];

  if (!commodity || !commodity.trim()) {
    errors.push("Commodity is required");
  } else if (commodity.trim().length > 100) {
    errors.push("Commodity must be 100 characters or less");
  }

  if (!state || !state.trim()) {
    errors.push("State is required");
  } else if (state.trim().length > 100) {
    errors.push("State must be 100 characters or less");
  }

  if (errors.length > 0) {
    throw new ApiError(400, errors.join("; "));
  }

  return {
    commodity: commodity.trim(),
    state: state.trim(),
  };
}