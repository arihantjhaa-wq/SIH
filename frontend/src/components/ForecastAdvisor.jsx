import React, { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Minus, RefreshCw, AlertCircle, Loader2 } from "lucide-react";
import { getForecast } from "../services/forecastService.js";
import PriceChart from "./PriceChart.jsx";
import { LiquidButton } from "./ui/liquid-glass-button";

export default function ForecastAdvisor({
  commodity,
  state,
  onSelectForecast,
}) {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!commodity || !state) {
      setForecast(null);
      setError(null);
      return;
    }
    const timer = setTimeout(() => {
      fetchForecast();
    }, 500);
    return () => clearTimeout(timer);
  }, [commodity, state]);

  async function fetchForecast() {
    setLoading(true);
    setError(null);
    try {
      const data = await getForecast({ commodity, state });
      setForecast(data);
    } catch (err) {
      setError(err.message || "Could not load forecast");
      setForecast(null);
    } finally {
      setLoading(false);
    }
  }

  // Not enough data
  if (!commodity || !state) {
    return null;
  }

  // Loading state
  if (loading) {
    return (
      <div className="border border-[#E4D6A7] bg-[#FBF7EC] p-4">
        <div className="flex items-center gap-2 text-sm text-[#8A8468]">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Analyzing market conditions…</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="border border-[#C4544A]/40 bg-[#FBF7EC] p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-[#C4544A] mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-[#C4544A]">{error}</p>
            <LiquidButton
              label="Try again"
              onClick={fetchForecast}
              size="xs"
              decor={false}
              className="mt-2 bg-transparent text-[#8A8468] underline hover:text-[#1B3A2B] hover:bg-transparent"
            />
          </div>
        </div>
      </div>
    );
  }

  // No forecast
  if (!forecast) {
    return null;
  }

  const { trend, forecast: forecastDays } = forecast;
  const prices = forecastDays.map((d) => d.predicted_price_inr_per_kg);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);

  const TrendIcon =
    trend?.direction === "rising"
      ? TrendingUp
      : trend?.direction === "falling"
        ? TrendingDown
        : Minus;

  const trendColor =
    trend?.direction === "rising"
      ? "#4A8F5A"
      : trend?.direction === "falling"
        ? "#C4544A"
        : "#8A8468";

  return (
    <div className="border border-[#E4D6A7] bg-[#FBF7EC] p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="ff-display text-base text-[#1B3A2B]">
            AI Market Pricing Advisor
          </h3>
          <p className="text-xs text-[#8A8468] mt-0.5">
            {commodity} · {state}
          </p>
        </div>
        <LiquidButton
          icon={<RefreshCw className="w-4 h-4" />}
          onClick={fetchForecast}
          aria-label="Refresh forecast"
          title="Refresh forecast"
          size="xs"
          decor={false}
          className="w-7 h-7 px-0 bg-transparent text-[#8A8468] hover:text-[#1B3A2B] hover:bg-transparent"
        />
      </div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-[#5C5842]">7-day outlook</span>
        <div
          className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
          style={{
            backgroundColor: `${trendColor}20`,
            color: trendColor,
          }}
        >
          <TrendIcon className="w-3 h-3" />
          <span className="capitalize">{trend?.direction}</span>
        </div>
      </div>
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-sm text-[#5C5842]">Current forecast range</span>
        <span className="font-medium text-[#1B3A2B] tabular">
          ₹{minPrice.toFixed(0)} — ₹{maxPrice.toFixed(0)} / kg
        </span>
      </div>
      <div className="bg-white border border-[#D8CBA1] px-3 py-2 mb-3">
        <p className="text-xs text-[#8A8468] mb-1">Suggested reference</p>
        <p className="text-lg font-medium text-[#1B3A2B] tabular">
          ₹{((minPrice + maxPrice) / 2).toFixed(0)} / kg
        </p>
      </div>
      {onSelectForecast && (
        <LiquidButton
          label="View detailed forecast →"
          onClick={() => onSelectForecast(forecast)}
          size="xs"
          decor={false}
          className="w-full bg-transparent text-[#1B3A2B] underline hover:text-[#C9A227] hover:bg-transparent"
        />
      )}
    </div>
  );
}
