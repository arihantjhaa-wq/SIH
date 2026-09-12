import React, { useState } from "react";
import {
  ArrowLeft,
  Calendar,
  Cloud,
  Thermometer,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  AlertCircle,
  RefreshCw,
  Download,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { getForecast } from "../services/forecastService.js";
import PriceChart from "../components/PriceChart.jsx";
import WeatherBadges, { WeatherBadgeRow } from "../components/WeatherBadges.jsx";
import commodities from "../data/commodities.json";
import { LiquidButton } from "../components/ui/liquid-glass-button";

const INDIAN_STATES = [
  "West Bengal", "Maharashtra", "Karnataka", "Telangana", "Tamil Nadu", "Andhra Pradesh",
  "Gujarat", "Rajasthan", "Uttar Pradesh", "Madhya Pradesh", "Kerala", "Punjab",
  "Haryana", "Odisha", "Assam", "Bihar", "Jharkhand", "Chhattisgarh", "Tripura",
  "Meghalaya", "Manipur", "Mizoram", "Nagaland", "Sikkim", "Arunachal Pradesh",
];

export default function MarketInsights({ onBack }) {
  const { user } = useAuth();
  const [commodity, setCommodity] = useState("");
  const [state, setState] = useState("West Bengal");
  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const handleSearch = async () => {
    if (!commodity || !state) {
      setError("Please select both a crop and state to search.");
      setForecastData(null);
      return;
    }
    setError(null);
    setLoading(true);
    setForecastData(null);
    try {
      const data = await getForecast({ commodity, state });
      setForecastData(data);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      setError(err.message || "Could not fetch forecast");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (!commodity || !state) return;
    handleSearch();
  };

  // Compute trend safely if the API response lacks the trend key
  const trend = forecastData?.trend || (() => {
    const list = forecastData?.forecast || [];
    if (list.length < 2) return null;
    const firstPrice = list[0].predicted_price_inr_per_kg;
    const lastPrice = list[list.length - 1].predicted_price_inr_per_kg;
    const pctChange = firstPrice !== 0 ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0;
    return {
      direction: pctChange > 0.5 ? "rising" : pctChange < -0.5 ? "falling" : "stable",
      change_percent: pctChange,
      first_price_inr: firstPrice,
      last_price_inr: lastPrice,
    };
  })();

  function handleDownloadCSV() {
    if (!forecastData) return;
    const csvRows = [];
    csvRows.push("Date,Predicted Price (₹/kg),Rainfall (mm),Temperature (°C)");
    (forecastData.forecast || []).forEach((day) => {
      csvRows.push(
        `${day.date},${(day.predicted_price_inr_per_kg ?? 0).toFixed(2)},${(day.rainfall_mm ?? 0).toFixed(1)},${(day.temperature_c ?? 0).toFixed(1)}`
      );
    });
    csvRows.push("");
    csvRows.push("SUMMARY");
    csvRows.push(`Commodity,${forecastData.commodity || ""}`);
    csvRows.push(`State,${forecastData.state || ""}`);
    csvRows.push(`Trend,${trend?.direction || "N/A"}`);
    csvRows.push(`Change Percentage,${trend?.change_percent != null ? trend.change_percent.toFixed(1) + "%" : "N/A"}`);
    csvRows.push(`Data Source,${forecastData.data_source || "N/A"}`);
    csvRows.push(`Generated,${lastUpdated || ""}`);
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${forecastData.commodity || "forecast"}_${forecastData.state || "data"}_7d_forecast.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      className="min-h-screen w-full bg-[#F3ECDD] text-[#2A2820]"
      style={{ fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif" }}
    >
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap'); .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; } .tabular { font-variant-numeric: tabular-nums; }`}</style>
      <div className="bg-[#14140F] text-[#F3ECDD] border-b border-[#33301F]">
        <div className="max-w-6xl mx-auto px-5 py-6">
          <div className="flex items-center justify-between gap-4">
            <LiquidButton
              label="Back"
              icon={<ArrowLeft className="w-3.5 h-3.5" />}
              onClick={onBack}
              size="xs"
              decor={false}
              className="bg-transparent text-[#C9C3AE] hover:text-[#C9A227] hover:bg-transparent border border-[#4A4630]"
            />
            <div className="flex items-center gap-3">
              {forecastData && (
                <LiquidButton
                  label="CSV"
                  icon={<Download className="w-3.5 h-3.5" />}
                  onClick={handleDownloadCSV}
                  size="xs"
                  decor={false}
                  className="bg-transparent text-[#C9A227] hover:bg-[#C9A227] hover:text-[#14140F] border border-[#C9A227]"
                />
              )}
              <LiquidButton
                label="Refresh"
                icon={<RefreshCw className="w-3.5 h-3.5" />}
                onClick={handleRefresh}
                disabled={loading || !commodity || !state}
                size="xs"
                decor={false}
                className="bg-transparent text-[#C9C3AE] hover:text-[#C9A227] hover:bg-transparent border border-[#4A4630]"
              />
            </div>
          </div>
          <div className="mt-8 max-w-xl">
            <h1 className="ff-display text-4xl sm:text-5xl leading-[1.08] text-[#F3ECDD]">Market Insights</h1>
            <p className="mt-4 text-[15px] leading-relaxed text-[#C9C3AE] max-w-md">
              7-day price forecasts based on weather, historical data, and market trends.
              Plan your purchases or set competitive prices with confidence.
            </p>
          </div>
        </div>
      </div>

      {/* Search Form */}
      <div className="max-w-6xl mx-auto px-5 pt-10 pb-8">
        <div className="bg-white border border-[#D8CBA1] p-6 shadow-sm">
          <h2 className="ff-display text-xl text-[#1B3A2B] mb-6 flex items-center gap-2">
            <Calendar className="w-5 h-5" /> Select Crop & State
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm text-[#5C5842] mb-2 font-medium">Commodity / Crop</label>
              <select
                value={commodity}
                onChange={(e) => setCommodity(e.target.value)}
                className="w-full border border-[#D8CBA1] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1B3A2B] cursor-pointer"
              >
                <option value="">Select a commodity</option>
                {commodities.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-[#5C5842] mb-2 font-medium">State</label>
              <select
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="w-full border border-[#D8CBA1] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1B3A2B] cursor-pointer"
              >
                <option value="">Select state</option>
                {INDIAN_STATES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-6 flex items-center gap-3">
            <LiquidButton
              label="Search"
              onClick={handleSearch}
              disabled={loading || !commodity || !state}
              size="md"
              className="px-6 disabled:opacity-60"
            />
            {error && !loading && (
              <div className="flex items-start gap-2 text-sm text-[#C4544A]">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}
          </div>
          {loading && (
            <div className="mt-6 flex items-center gap-2 text-[#8A8468]">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Analyzing market conditions...</span>
            </div>
          )}
        </div>
      </div>

      {/* Forecast Results */}
      {forecastData && (
        <div className="max-w-6xl mx-auto px-5 pb-16">
          <div className="border border-[#E4D6A7] bg-[#FBF7EC] shadow-sm">
            <div className="border-b border-[#D8CBA1] p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="ff-display text-2xl text-[#1B3A2B]">{forecastData.commodity}</h2>
                  <p className="text-sm text-[#8A8468] mt-1">{forecastData.state}</p>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-[#8A8468] uppercase tracking-wide">Forecast Source</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-medium ${
                        forecastData.data_source === "model"
                          ? "bg-[#4A8F5A]/20 text-[#4A8F5A]"
                          : "bg-[#C9A227]/20 text-[#8A6D1E]"
                      }`}
                    >
                      {forecastData.data_source === "model" ? "Model-Based" : "Fallback"}
                    </span>
                  </div>
                  {lastUpdated && (
                    <p className="text-[10px] text-[#8A8468] mt-2">
                      Updated {new Date(lastUpdated).toLocaleTimeString("en-IN")}
                    </p>
                  )}
                </div>
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                <div className="lg:col-span-1 bg-white border border-[#D8CBA1] p-5">
                  <h3 className="ff-display text-lg text-[#1B3A2B] mb-4">Market Trend</h3>
                  {trend ? (
                    <>
                      <div className="flex items-center gap-3 mb-4">
                        {trend.direction === "rising" ? (
                          <TrendingUp className="w-8 h-8 text-[#4A8F5A]" />
                        ) : trend.direction === "falling" ? (
                          <TrendingDown className="w-8 h-8 text-[#C4544A]" />
                        ) : (
                          <Minus className="w-8 h-8 text-[#8A8468]" />
                        )}
                        <div>
                          <span className="text-sm text-[#5C5842]">Trend</span>
                          <div className="flex items-baseline gap-2">
                            <span
                              className={`text-2xl font-medium ${
                                trend.direction === "rising"
                                  ? "text-[#4A8F5A]"
                                  : trend.direction === "falling"
                                    ? "text-[#C4544A]"
                                    : "text-[#8A8468]"
                              }`}
                            >
                              {(trend.direction || "STABLE").toUpperCase()}
                            </span>
                            <span
                              className={`tabular ${
                                (trend.change_percent ?? 0) > 0
                                  ? "text-[#4A8F5A]"
                                  : (trend.change_percent ?? 0) < 0
                                    ? "text-[#C4544A]"
                                    : "text-[#8A8468]"
                              }`}
                            >
                              {(trend.change_percent ?? 0) > 0 ? "+" : ""}
                              {(trend.change_percent ?? 0).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <span className="text-xs text-[#8A8468]">First Day</span>
                          <p className="tabular text-lg text-[#1B3A2B]">
                            ₹{(trend.first_price_inr ?? 0).toFixed(2)}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs text-[#8A8468]">Last Day</span>
                          <p className="tabular text-lg text-[#1B3A2B]">
                            ₹{(trend.last_price_inr ?? 0).toFixed(2)}
                          </p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-[#8A8468] py-4">Trend data unavailable.</p>
                  )}
                </div>
                <div className="lg:col-span-2">
                  <PriceChart forecast={forecastData.forecast || []} trend={trend} />
                </div>
              </div>

              <div className="mb-8">
                <h3 className="ff-display text-lg text-[#1B3A2B] mb-4 flex items-center gap-2">
                  <Cloud className="w-5 h-5" /> 7-Day Weather Forecast
                </h3>
                <WeatherBadgeRow forecast={forecastData.forecast || []} />
              </div>

              <div className="border-t border-[#D8CBA1] pt-6">
                <h3 className="ff-display text-lg text-[#1B3A2B] mb-4">Day-by-Day Forecast</h3>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="bg-[#FBF7EC]">
                        <th className="border-b border-[#D8CBA1] p-2 text-left text-xs uppercase tracking-wide text-[#8A8468] font-medium">Date</th>
                        <th className="border-b border-[#D8CBA1] p-2 text-left text-xs uppercase tracking-wide text-[#8A8468] font-medium">Price (₹/kg)</th>
                        <th className="border-b border-[#D8CBA1] p-2 text-left text-xs uppercase tracking-wide text-[#8A8468] font-medium">Rainfall (mm)</th>
                        <th className="border-b border-[#D8CBA1] p-2 text-left text-xs uppercase tracking-wide text-[#8A8468] font-medium">Temp (°C)</th>
                        <th className="border-b border-[#D8CBA1] p-2 text-left text-xs uppercase tracking-wide text-[#8A8468] font-medium">Weather Impact</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(forecastData.forecast || []).map((day, idx) => (
                        <tr key={idx}>
                          <td className="p-2 border-b border-[#D8CBA1]/30">
                            {new Date(day.date).toLocaleDateString("en-IN", {
                              weekday: "short",
                              day: "numeric",
                              month: "short",
                            })}
                          </td>
                          <td className="p-2 border-b border-[#D8CBA1]/30 tabular font-medium text-[#1B3A2B]">
                            ₹{(day.predicted_price_inr_per_kg ?? 0).toFixed(2)}
                          </td>
                          <td className="p-2 border-b border-[#D8CBA1]/30 tabular">{(day.rainfall_mm ?? 0).toFixed(1)} mm</td>
                          <td className="p-2 border-b border-[#D8CBA1]/30 tabular">{(day.temperature_c ?? 0).toFixed(1)}°C</td>
                          <td className="p-2 border-b border-[#D8CBA1]/30">
                            <div className="flex items-center gap-1.5">
                              {day.rainfall_mm > 5 && (
                                <span className="inline-flex items-center gap-0.5 text-[10px] bg-[#4A90A4]/15 text-[#4A90A4] px-1.5 py-0.5 rounded">
                                  <Cloud className="w-2.5 h-2.5" /> Wet
                                </span>
                              )}
                              {day.temperature_c > 35 && (
                                <span className="inline-flex items-center gap-0.5 text-[10px] bg-[#C4544A]/15 text-[#C4544A] px-1.5 py-0.5 rounded">
                                  <Thermometer className="w-2.5 h-2.5" /> Hot
                                </span>
                              )}
                              {day.rainfall_mm <= 2 && day.temperature_c <= 30 && (
                                <span className="text-[10px] text-[#8A8468]">Normal</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-[#D8CBA1]/30">
                <h4 className="text-sm text-[#8A8468] uppercase tracking-wide mb-2">Notes</h4>
                <ul className="text-xs text-[#5C5842] space-y-1">
                  <li>• Forecasts are based on 7-day weather outlook and historical market data.</li>
                  <li>• When historical data for the commodity/state is insufficient, a deterministic fallback model is used.</li>
                  <li>• Weather data sourced from Open-Meteo (free public API).</li>
                  <li>• Forecasts should be used as guidance; actual market prices may vary.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
