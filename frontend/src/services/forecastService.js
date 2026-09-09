/**
 * Fetch 7-day price forecast from the backend proxy.
 * Uses commodity + state only (location removed per requirements).
 */
import api from "./api";

export async function getForecast({ commodity, state }) {
  const response = await api.post("/forecast/predict", {
    commodity,
    state,
  });
  // response.data is { success: true, data: {...} }
  // return the inner data payload directly
  return response.data?.data ?? response.data;
}

export async function checkForecastHealth() {
  const response = await api.get("/forecast/health");
  return response.data?.data ?? response.data;
}
