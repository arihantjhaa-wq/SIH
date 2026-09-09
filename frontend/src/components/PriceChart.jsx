import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

/**
 * PriceChart - Displays 7-day price forecast with exact API values.
 *
 * CRITICAL: This chart displays EXACT values from the API response.
 * No interpolation, smoothing, or fabrication of data points.
 */
export default function PriceChart({ forecast, trend, compact = false }) {
  if (!forecast || forecast.length === 0) {
    return (
      <div className="text-sm text-[#8A8468] text-center py-8">
        No forecast data available
      </div>
    );
  }

  // Format data for Recharts - use EXACT API values
  const chartData = forecast.map((day) => ({
    date: formatDate(day.date),
    fullDate: day.date,
    price: day.predicted_price_inr_per_kg,
    rainfall: day.rainfall_mm,
    temperature: day.temperature_c,
  }));

  // Calculate Y-axis domain with padding
  const prices = chartData.map((d) => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.15 || 5; // 15% padding or min 5
  const yMin = Math.floor(minPrice - padding);
  const yMax = Math.ceil(maxPrice + padding);

  // Trend icon
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
    <div className="w-full">
      {/* Chart */}
      <div className={compact ? "h-48" : "h-64"}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#E4D6A7"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              stroke="#8A8468"
              tick={{ fontSize: 11, fill: "#5C5842" }}
              tickLine={false}
              axisLine={{ stroke: "#D8CBA1" }}
            />
            <YAxis
              domain={[yMin, yMax]}
              stroke="#8A8468"
              tick={{ fontSize: 11, fill: "#5C5842" }}
              tickLine={false}
              axisLine={{ stroke: "#D8CBA1" }}
              tickFormatter={(val) => `₹${val}`}
              width={50}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#1B3A2B"
              strokeWidth={2}
              dot={{
                fill: "#1B3A2B",
                stroke: "#C9A227",
                strokeWidth: 2,
                r: 4,
              }}
              activeDot={{
                fill: "#C9A227",
                stroke: "#1B3A2B",
                strokeWidth: 2,
                r: 6,
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Trend Summary */}
      {trend && (
        <div
          className={`flex items-center justify-center gap-2 mt-3 ${
            compact ? "text-xs" : "text-sm"
          }`}
        >
          <TrendIcon
            className={compact ? "w-3.5 h-3.5" : "w-4 h-4"}
            style={{ color: trendColor }}
          />
          <span className="font-medium" style={{ color: trendColor }}>
            {trend.direction.charAt(0).toUpperCase() + trend.direction.slice(1)}
          </span>
          <span className="text-[#5C5842]">
            {trend.change_percent > 0 ? "+" : ""}
            {trend.change_percent.toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Custom tooltip - displays exact values from API.
 */
function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-[#14140F] text-[#F3ECDD] px-3 py-2 text-xs shadow-lg border border-[#C9A227]/40">
      <p className="font-medium mb-1">{data.fullDate}</p>
      <p className="tabular">
        <span className="text-[#C9A227]">₹{data.price.toFixed(2)}</span> / kg
      </p>
      <p className="text-[#C9C3AE] mt-1">
        🌧 {data.rainfall.toFixed(1)} mm · 🌡 {data.temperature.toFixed(1)}°C
      </p>
    </div>
  );
}

/**
 * Format date for X-axis labels.
 */
function formatDate(isoDate) {
  const date = new Date(isoDate);
  const day = date.getDate();
  const month = date.toLocaleString("en-IN", { month: "short" });
  return `${day} ${month}`;
}
