import React, { useEffect, useMemo, useState } from "react";
import { ArrowLeft, BadgePercent, Sprout, MapPin, MessageSquare, Plus, Minus, Loader2, AlertCircle } from "lucide-react";
import { discountPct, money, MAX_SAVER_THRESHOLD } from "../utils/marketplace.js";
import { generateDescription, generateReviews, avgRating, timeAgo } from "../utils/productContent.js";
import { getForecast } from "../services/forecastService.js";
import PriceChart from "../components/PriceChart.jsx";
import WeatherBadges from "../components/WeatherBadges.jsx";
import ProductPhoto from "../components/ProductPhoto.jsx";
import StarRow from "../components/StarRow.jsx";
import ProductCard from "../components/ProductCard.jsx";
import { LiquidButton } from "../components/ui/liquid-glass-button";
import axios from 'axios';


export default function ProductDetailPage({
  product,
  allProducts,
  cart,
  isBusiness,
  bizUnlocked,
  onAddToCart,
  onSetQty,
  onBack,
  onOpenProduct,
}) {
  const qtyInCart = cart[product.id] || 0;
  const description = useMemo(() => generateDescription(product), [product]);
  const reviews = useMemo(() => generateReviews(product), [product]);
  const rating = useMemo(() => avgRating(reviews), [reviews]);

  // --- Forecast state ---
  const [forecastData, setForecastData] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState(null);

  const similar = useMemo(
    () =>
      allProducts
        .filter((p) => p.id !== product.id && p.category === product.category)
        .slice(0, 4),
    [allProducts, product],
  );

  const disc = discountPct(product);
  const showMaxSaver = isBusiness && disc >= MAX_SAVER_THRESHOLD;
  const displayPrice = isBusiness
    ? bizUnlocked
      ? product.bizPrice
      : product.indivPrice
    : product.indivPrice;

  // --- Fetch forecast on mount ---
  useEffect(() => {
    async function loadForecast() {
      // Extract location from product.farmer (format: "Name, Location")
      const farmerParts = product.farmer.split(",");
      const location = farmerParts.length >= 2 ? farmerParts[1].trim() : null;
      const commodity = product.name;

      if (!location || !commodity) {
        return; // Not enough info
      }

      setForecastLoading(true);
      setForecastError(null);

      try {
        // For MVP, guess state from location
        const state = guessStateFromLocation(location);
        if (!state) {
          setForecastError(null); // Silently skip
          return;
        }

        const data = await getForecast({ commodity, state });
        setForecastData(data);
      } catch (err) {
        console.error("Forecast fetch failed:", err);
        setForecastError(err.message || "Could not load forecast");
      } finally {
        setForecastLoading(false);
      }
    }

    loadForecast();
  }, [product]);

  return (
    <main className="max-w-6xl mx-auto px-5 py-10">
      <LiquidButton
        label="Back to catalogue"
        icon={<ArrowLeft className="w-3.5 h-3.5" />}
        onClick={onBack}
        size="xs"
        decor={false}
        className="bg-transparent text-[#5C5842] hover:text-[#1B3A2B] hover:bg-transparent"
      />

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-10">
        <div className="relative">
          {showMaxSaver && (
            <span className="absolute top-3 right-3 z-10 flex items-center gap-1 bg-[#C9A227] text-[#14140F] text-[11px] px-2 py-0.5">
              <BadgePercent className="w-3 h-3" /> Max Saver
            </span>
          )}
          {product.farmerAdded && (
            <span className="absolute top-3 left-3 z-10 flex items-center gap-1 bg-[#1B3A2B] text-[#F3ECDD] text-[11px] px-2 py-0.5">
              <Sprout className="w-3 h-3" /> New listing
            </span>
          )}
          <ProductPhoto
            product={product}
            className="w-full h-72 sm:h-96 object-cover border border-[#E4D6A7]"
          />
        </div>

        <div>
          <h1 className="ff-display text-3xl sm:text-4xl leading-tight">
            {product.name}
          </h1>
          <div className="flex items-center gap-2 mt-2 text-sm text-[#5C5842]">
            <MapPin className="w-3.5 h-3.5" />
            {product.farmer}
          </div>

          {reviews.length > 0 && (
            <div className="flex items-center gap-2 mt-3">
              <StarRow rating={rating} />
              <span className="text-sm text-[#5C5842] tabular">
                {rating.toFixed(1)} · {reviews.length} review
                {reviews.length !== 1 ? "s" : ""}
              </span>
            </div>
          )}

          <div className="mt-5 flex items-baseline gap-1.5">
            <span className="ff-display text-3xl tabular text-[#1B3A2B]">
              {money(displayPrice)}
            </span>
            <span className="text-sm text-[#5C5842]">/ {product.unit}</span>
            {isBusiness && bizUnlocked && (
              <span className="text-sm text-[#8A6D1E] line-through tabular ml-1">
                {money(product.indivPrice)}
              </span>
            )}
          </div>

          {isBusiness ? (
            <p className="text-xs text-[#8A6D1E] mt-1">
              {bizUnlocked
                ? `Bulk only — min ${product.minBulkQty} ${product.unit}`
                : "Verify GSTIN to see business rate"}
            </p>
          ) : (
            <p className="text-xs text-[#8A6D1E] mt-1">
              Business rate: {money(product.bizPrice)}/{product.unit} — min{" "}
              {product.minBulkQty} {product.unit}
            </p>
          )}

          <p className="text-sm text-[#5C5842] leading-relaxed mt-5">
            {description}
          </p>

          <div className="mt-6 max-w-xs">
            {qtyInCart > 0 ? (
              <div className="flex items-center justify-between border border-[#D8CBA1] px-2 py-1.5">
                <LiquidButton
                  icon={<Minus className="w-3.5 h-3.5" />}
                  onClick={() => onSetQty(product, qtyInCart - (isBusiness ? 5 : 1))}
                  size="xs"
                  decor={false}
                  className="w-8 h-8 px-0"
                />
                <span className="text-sm tabular">
                  {qtyInCart} {product.unit}
                </span>
                <LiquidButton
                  icon={<Plus className="w-3.5 h-3.5" />}
                  onClick={() => onSetQty(product, qtyInCart + (isBusiness ? 5 : 1))}
                  size="xs"
                  decor={false}
                  className="w-8 h-8 px-0"
                />
              </div>
            ) : (
              <LiquidButton
                label={isBusiness ? "Add bulk order" : "Add to cart"}
                onClick={() => onAddToCart(product)}
                className="w-full"
              />
            )}
          </div>
        </div>
      </div>

      {/* 7-Day Price & Weather Trend */}
      {(forecastData || forecastLoading || forecastError) && (
        <section className="mt-14 max-w-3xl">
          <div className="border border-[#E4D6A7] bg-[#FBF7EC] p-5 sm:p-6 shadow-sm">
            <h2 className="ff-display text-2xl mb-1 text-[#1B3A2B]">
              7-Day Price & Weather Trend
            </h2>
            <p className="text-sm text-[#8A8468] mb-6">
              {product.name} · MARKET FORECAST
            </p>

            {forecastLoading ? (
              <div className="flex flex-col items-center justify-center py-10 text-[#8A8468]">
                <Loader2 className="w-6 h-6 animate-spin mb-2 text-[#C9A227]" />
                <p className="text-sm">Preparing 7-day market outlook...</p>
              </div>
            ) : forecastError ? (
              <div className="flex items-start gap-2 p-4 border border-[#C4544A]/30 bg-[#C4544A]/10">
                <AlertCircle className="w-5 h-5 text-[#C4544A] flex-shrink-0" />
                <div>
                  <p className="text-sm text-[#C4544A]">{forecastError}</p>
                </div>
              </div>
            ) : forecastData ? (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="md:col-span-3">
                  <PriceChart
                    forecast={forecastData.forecast}
                    trend={forecastData.trend}
                  />
                </div>
                <div className="md:col-span-1 border-t md:border-t-0 md:border-l border-[#D8CBA1] pt-4 md:pt-0 md:pl-4 flex flex-col justify-center">
                  <h3 className="text-xs uppercase tracking-wide text-[#8A8468] font-medium mb-3">
                    Daily Weather
                  </h3>
                  <div className="space-y-3">
                    {forecastData.forecast.slice(0, 3).map((day, idx) => (
                      <div key={idx} className="flex flex-col">
                        <span className="text-[11px] text-[#5C5842] mb-0.5 font-medium">
                          {new Date(day.date).toLocaleString('en-IN', { weekday: 'short', day: 'numeric' })}
                        </span>
                        <WeatherBadges
                          rainfall={day.rainfall_mm}
                          temperature={day.temperature_c}
                          compact
                        />
                      </div>
                    ))}
                    {forecastData.forecast.length > 3 && (
                      <p className="text-[10px] text-[#8A8468] pt-1">
                        + {forecastData.forecast.length - 3} more days...
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </section>
      )}

      <section className="mt-14 max-w-3xl">
        <div className="flex items-center gap-2 mb-5">
          <MessageSquare className="w-4 h-4 text-[#1B3A2B]" />
          <h2 className="ff-display text-2xl">Reviews</h2>
        </div>
        {reviews.length === 0 ? (
          <p className="text-sm text-[#5C5842]">No reviews yet.</p>
        ) : (
          <div className="space-y-4">
            {reviews.map((r) => (
              <div key={r.id} className="border border-[#E4D6A7] bg-[#FBF7EC] p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{r.name}</span>
                  <span className="text-xs text-[#8A8468]">
                    {timeAgo(r.daysAgo)}
                  </span>
                </div>
                <div className="mt-1.5">
                  <StarRow rating={r.rating} />
                </div>
                <p className="text-sm text-[#5C5842] leading-relaxed mt-2">
                  {r.text}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      {similar.length > 0 && (
        <section className="mt-14">
          <h2 className="ff-display text-2xl mb-5">You may also like</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {similar.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                isBusiness={isBusiness}
                bizUnlocked={bizUnlocked}
                qtyInCart={cart[p.id] || 0}
                onAdd={() => onAddToCart(p)}
                onSetQty={(q) => onSetQty(p, q)}
                onOpen={() => onOpenProduct(p)}
              />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

/**
 * Guess state from a location name using common Indian mappings.
 * For MVP, this is a simple lookup. In production, use structured data.
 */
function guessStateFromLocation(location) {
  const locationLower = location.toLowerCase();

  // Major Indian cities → states mapping
  const cityStateMap = {
    kolkata: "West Bengal",
    calcutta: "West Bengal",
    delhi: "Delhi",
    mumbai: "Maharashtra",
    bombay: "Maharashtra",
    bangalore: "Karnataka",
    bengaluru: "Karnataka",
    hyderabad: "Telangana",
    Chennai: "Tamil Nadu",
    madras: "Tamil Nadu",
    pune: "Maharashtra",
    ahmedabad: "Gujarat",
    surat: "Gujarat",
    jaipur: "Rajasthan",
    lucknow: "Uttar Pradesh",
    chandigarh: "Chandigarh",
    kochi: "Kerala",
    cochin: "Kerala",
    thiruvananthapuram: "Kerala",
    bhubaneswar: "Odisha",
    guwahati: "Assam",
    patna: "Bihar",
    ranchi: "Jharkhand",
    bhopal: "Madhya Pradesh",
    indore: "Madhya Pradesh",
    nagpur: "Maharashtra",
    visakhapatnam: "Andhra Pradesh",
    vijayawada: "Andhra Pradesh",
    coimbatore: "Tamil Nadu",
    madurai: "Tamil Nadu",
    salem: "Tamil Nadu",
  };

  // Direct lookup
  if (cityStateMap[locationLower]) {
    return cityStateMap[locationLower];
  }

  // If location itself looks like a state, return it
  const stateNames = [
    "West Bengal",
    "Maharashtra",
    "Karnataka",
    "Telangana",
    "Tamil Nadu",
    "Andhra Pradesh",
    "Gujarat",
    "Rajasthan",
    "Uttar Pradesh",
    "Madhya Pradesh",
    "Kerala",
    "Punjab",
    "Haryana",
    "Odisha",
    "Assam",
    "Bihar",
    "Jharkhand",
    "Chhattisgarh",
    "Tripura",
    "Meghalaya",
    "Manipur",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Arunachal Pradesh",
    "Delhi",
    "Chandigarh",
  ];

  for (const state of stateNames) {
    if (locationLower.includes(state.toLowerCase())) {
      return state;
    }
  }

  return null;
}
