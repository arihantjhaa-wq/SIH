import React from "react";
import { CloudRain, Thermometer, Droplets } from "lucide-react";

/**
 * WeatherBadges - Display weather data for a forecast day.
 */
export default function WeatherBadges({ rainfall, temperature, compact = false }) {
  return (
    <div
      className={`flex items-center gap-3 ${
        compact ? "text-xs" : "text-sm"
      } text-[#5C5842]`}
    >
      <div className="flex items-center gap-1">
        <CloudRain
          className={compact ? "w-3 h-3" : "w-4 h-4"}
          style={{ color: "#4A90A4" }}
        />
        <span className="tabular">{rainfall.toFixed(1)} mm</span>
      </div>
      <div className="flex items-center gap-1">
        <Thermometer
          className={compact ? "w-3 h-3" : "w-4 h-4"}
          style={{ color: "#C4544A" }}
        />
        <span className="tabular">{temperature.toFixed(1)}°C</span>
      </div>
    </div>
  );
}

/**
 * WeatherBadgeRow - Display weather for all forecast days.
 */
export function WeatherBadgeRow({ forecast }) {
  if (!forecast || forecast.length === 0) return null;

  return (
    <div className="flex items-center justify-between mt-3 px-1">
      <div className="flex items-center gap-1.5 text-xs text-[#8A8468]">
        <Droplets className="w-3 h-3" style={{ color: "#4A90A4" }} />
        <span>Avg rainfall</span>
        <span className="font-medium text-[#5C5842] tabular">
          {(
            forecast.reduce((sum, d) => sum + d.rainfall_mm, 0) / forecast.length
          ).toFixed(1)}{" "}
          mm
        </span>
      </div>
      <div className="flex items-center gap-1.5 text-xs text-[#8A8468]">
        <Thermometer className="w-3 h-3" style={{ color: "#C4544A" }} />
        <span>Avg temp</span>
        <span className="font-medium text-[#5C5842] tabular">
          {(
            forecast.reduce((sum, d) => sum + d.temperature_c, 0) / forecast.length
          ).toFixed(1)}
          °C
        </span>
      </div>
    </div>
  );
}
