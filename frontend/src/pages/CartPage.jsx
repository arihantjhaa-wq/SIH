import React, { useState, useEffect } from "react";
import {
  ShoppingCart,
  ArrowLeft,
  Plus,
  Minus,
  Trash2,
  Truck,
  MapPin,
  Clock,
  Fuel,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Package,
} from "lucide-react";
import { money } from "../utils/marketplace.js";
import ProductPhoto from "../components/ProductPhoto.jsx";
import {
  fetchTransportPreview,
  createTransportOrder,
} from "../services/transportService.js";
import { useCart } from "../context/CartContext.jsx";

// ---------------------------------------------------------------------------
// Helpers: Loading / Error / Transport display components
// ---------------------------------------------------------------------------

function TransportLoadingState() {
  return (
    <div className="border border-[#E4D6A7] bg-[#FFFDF3] p-6 text-center">
      <Loader2 className="w-6 h-6 mx-auto animate-spin text-[#C9A227] mb-2" />
      <p className="text-sm text-[#5C5842]">Calculating delivery route…</p>
    </div>
  );
}

function TransportErrorState({ message, onRetry }) {
  return (
    <div className="border border-[#F0A5A5] bg-[#FFF5F5] p-5">
      <div className="flex items-start gap-2">
        <AlertCircle className="w-4 h-4 text-[#C4544A] mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-xs font-medium text-[#C4544A] uppercase tracking-wide">
            Delivery unavailable
          </p>
          <p className="text-sm text-[#5C5842] mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 text-xs text-[#1B3A2B] underline hover:text-[#0E1F17]"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function TransportBreakdown({ shipment }) {
  const t = shipment.transportation;
  if (!t) return null;
  return (
    <div className="border border-[#E4D6A7] bg-[#FFFDF3] overflow-hidden">
      {/* Header: Farmer → Destination */}
      <div className="px-4 py-3 border-b border-[#E4D6A7] flex items-center gap-2">
        <Truck className="w-4 h-4 text-[#1B3A2B]" />
        <span className="text-xs font-medium uppercase tracking-wide text-[#1B3A2B]">
          {shipment.farmerName}
          {shipment.quantityDisplay && (
            <span className="ml-2 text-[11px] text-[#8A8468] font-normal normal-case">
              {shipment.quantityDisplay}
            </span>
          )}
        </span>
      </div>

      {/* Route */}
      <div className="px-4 pt-4 pb-2 space-y-2">
        <div className="flex gap-2">
          <MapPin className="w-3.5 h-3.5 text-[#C9A227] mt-0.5 shrink-0" />
          <div>
            <p className="text-[11px] uppercase tracking-wide text-[#8A8468]">Origin</p>
            <p className="text-sm text-[#2A2820] leading-snug">{t.origin_address}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 pl-4 text-[11px] text-[#8A8468]">
          <span className="w-px h-4 bg-[#E4D6A7]" />
          <span className="tabular">{t.distance_display} • {t.active_travel_display}</span>
        </div>
        <div className="flex gap-2">
          <MapPin className="w-3.5 h-3.5 text-[#1B3A2B] mt-0.5 shrink-0" />
          <div>
            <p className="text-[11px] uppercase tracking-wide text-[#8A8468]">Destination</p>
            <p className="text-sm text-[#2A2820] leading-snug">{t.destination_address}</p>
          </div>
        </div>
      </div>

      {/* Timing */}
      <div className="mx-4 mt-3 mb-3 border border-[#E4D6A7] bg-white overflow-hidden">
        <div className="grid grid-cols-2 text-xs">
          <div className="px-3 py-2 border-r border-[#E4D6A7]">
            <p className="text-[11px] uppercase tracking-wide text-[#8A8468]">Scheduled Departure</p>
            <p className="text-sm text-[#2A2820] tabular mt-0.5">{t.scheduled_departure_display}</p>
          </div>
          <div className="px-3 py-2">
            <p className="text-[11px] uppercase tracking-wide text-[#8A8468]">Estimated Arrival</p>
            <p className="text-sm text-[#1B3A2B] font-medium tabular mt-0.5">{t.estimated_arrival_display}</p>
          </div>
          <div className="px-3 py-2 border-r border-t border-[#E4D6A7]">
            <p className="text-[11px] uppercase tracking-wide text-[#8A8468]">Travel Time</p>
            <p className="text-sm text-[#5C5842] tabular mt-0.5">{t.active_travel_display}</p>
          </div>
          <div className="px-3 py-2 border-t border-[#E4D6A7]">
            <p className="text-[11px] uppercase tracking-wide text-[#8A8468]">Total Transit</p>
            <p className="text-sm text-[#5C5842] tabular mt-0.5">{t.total_transit_display}</p>
          </div>
          {t.layover_display && t.layover_display !== "None" && (
            <div className="col-span-2 px-3 py-2 border-t border-[#E4D6A7] text-[11px] text-[#8A8468]">
              <Clock className="w-3 h-3 inline-block mr-1" />
              Mandatory rest: {t.layover_display}
            </div>
          )}
        </div>
      </div>

      {/* Vehicle */}
      <div className="mx-4 mb-3 flex items-center gap-2">
        <div className="w-8 h-8 bg-[#1B3A2B] text-[#C9A227] flex items-center justify-center">
          <Truck className="w-4 h-4" />
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[#8A8468]">Vehicle</p>
          <p className="text-sm text-[#2A2820] leading-snug">{t.vehicle?.name}</p>
        </div>
      </div>

      {/* Cost breakdown */}
      <div className="border-t border-[#E4D6A7] bg-white">
        <div className="px-4 py-3 space-y-1.5 text-sm">
          <div className="flex justify-between tabular">
            <span className="text-[#5C5842] flex items-center gap-1">
              <Fuel className="w-3 h-3" /> {t.fuel_type} Expense
            </span>
            <span className="text-[#2A2820]">{t.fuel_cost_display}</span>
          </div>
          <div className="flex justify-between tabular">
            <span className="text-[#5C5842]">FASTag Tolls</span>
            <span className="text-[#2A2820]">{t.toll_cost_display}</span>
          </div>
          <div className="flex justify-between tabular">
            <span className="text-[#5C5842]">Maintenance & Servicing</span>
            <span className="text-[#2A2820]">{t.maintenance_cost_display}</span>
          </div>
          <div className="border-t border-[#E4D6A7] my-2" />
          <div className="flex justify-between tabular font-medium">
            <span className="text-[#1B3A2B]">Transportation Total</span>
            <span className="text-[#1B3A2B]">{t.total_transportation_cost_display}</span>
          </div>
        </div>
      </div>

      {/* Map / polyline preview (visual route hint when available) */}
      {t.route_points && t.route_points.length > 0 && (
        <MiniRouteMap points={t.route_points} />
      )}
    </div>
  );
}

function MiniRouteMap({ points }) {
  if (!points || points.length < 2) return null;

  // Compute bounding box
  const lats = points.map((p) => p.lat);
  const lngs = points.map((p) => p.lng);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const latRange = maxLat - minLat || 0.01;
  const lngRange = maxLng - minLng || 0.01;

  const W = 280;
  const H = 120;
  const P = 20; // padding

  const toXY = (pt) => {
    const x = P + ((pt.lng - minLng) / lngRange) * (W - P * 2);
    const y = H - P - ((pt.lat - minLat) / latRange) * (H - P * 2);
    return { x, y };
  };

  const polylinePoints = points.map(toXY).map((p) => `${p.x},${p.y}`).join(" ");
  const origin = toXY(points[0]);
  const dest = toXY(points[points.length - 1]);

  return (
    <div className="border-t border-[#E4D6A7] bg-[#FAF6E8]">
      <div className="px-4 py-2">
        <p className="text-[10px] uppercase tracking-wide text-[#8A8468] mb-2">Route Overview</p>
      </div>
      <svg
        width="100%"
        viewBox={`0 0 ${W} ${H}`}
        className="block w-full max-w-full"
        style={{ height: H, minHeight: H }}
        xmlns="http://www.w3.org/2000/svg"
      >
        <polyline
          fill="none"
          stroke="#C9A227"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          opacity="0.95"
          points={polylinePoints}
        />
        <circle cx={origin.x} cy={origin.y} r="4.5" fill="#1B3A2B" opacity="0.9" />
        <circle cx={origin.x} cy={origin.y} r="2" fill="#C9A227" />
        <circle cx={dest.x} cy={dest.y} r="4.5" fill="#C4544A" opacity="0.9" />
        <circle cx={dest.x} cy={dest.y} r="2" fill="#F3ECDD" />
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Cart Page
// ---------------------------------------------------------------------------

export default function CartPage({
  cartLines,
  isBusiness,
  bizUnlocked,
  priceFor,
  subtotal,
  savings,
  bizUnlockedSavings,
  setQty,
  removeFromCart,
  onBack,
}) {
  const { cart } = useCart();
  const [orderPlaced, setOrderPlaced] = useState(null);

  // ---- Transportation preview state ----
  const [transport, setTransport] = useState(null);
  const [transportLoading, setTransportLoading] = useState(false);
  const [transportError, setTransportError] = useState(null);
  const [placingOrder, setPlacingOrder] = useState(false);
  const [orderError, setOrderError] = useState(null);

  const hasLines = cartLines.length > 0;
  const pricingTier = isBusiness && bizUnlocked ? "business" : "individual";

  const cartCartLength = cartLines.length;
  const cartQuantities = cartLines.map((l) => [l.product.id, l.qty].join(":")).join("|");
  const cartKey = `${cartCartLength}:${cartQuantities}:${pricingTier}`;

  const fetchPreview = async () => {
    if (!hasLines) return;
    setTransportLoading(true);
    setTransportError(null);
    try {
      const result = await fetchTransportPreview(cart, pricingTier);
      setTransport(result);
    } catch (err) {
      const msg =
        err?.response?.data?.message ||
        err?.message ||
        "We couldn't calculate the delivery route right now. Please try again in a moment.";
      setTransport((prev) => prev || null);
      setTransportError(msg);
    } finally {
      setTransportLoading(false);
    }
  };

  useEffect(() => {
    if (!hasLines) {
      setTransport(null);
      setTransportError(null);
      setTransportLoading(false);
      return;
    }
    fetchPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cartKey]);

  async function handlePlaceOrder() {
    setOrderError(null);
    setPlacingOrder(true);
    try {
      const result = await createTransportOrder(cart, pricingTier);
      setOrderPlaced(result.order || result);
    } catch (err) {
      // For quote-with-retry case (e.g. transient Google failure), also re-fetch preview.
      const msg =
        err?.response?.data?.message ||
        err?.message ||
        "We couldn't place your order right now. Please try again in a moment.";
      setOrderError(msg);
      // If create failed but checkout should recover, re-fetch the transport preview
      fetchPreview();
    } finally {
      setPlacingOrder(false);
    }
  }

  // ---- Order-placed confirmation screen -----------------------------------
  if (orderPlaced) {
    const placedShipments = Array.isArray(orderPlaced.shipments)
      ? orderPlaced.shipments
      : [];
    return (
      <main className="max-w-3xl mx-auto px-5 py-10">
        <div className="border border-[#E4D6A7] bg-[#FBF7EC] px-6 py-10">
          <CheckCircle2 className="w-10 h-10 text-[#1B3A2B] mx-auto mb-4" />
          <h1 className="ff-display text-2xl text-center">
            Order placed — thank you!
          </h1>
          <p className="text-sm text-center text-[#5C5842] mt-2">
            {orderPlaced.orderNumber ? (
              <span>
                Order <span className="font-medium text-[#1B3A2B]">{orderPlaced.orderNumber}</span>
                {" · "}
                Total {money(orderPlaced.grandTotal ?? subtotal)}
              </span>
            ) : (
              <span>Your order of {money(subtotal)} has been received.</span>
            )}
            {" "}The farmer will be notified and your produce will be on its way.
          </p>

          {placedShipments.length > 0 && (
            <div className="mt-8 space-y-4">
              <h2 className="text-xs font-medium uppercase tracking-wide text-[#8A8468]">Delivery overview</h2>
              {placedShipments.map((s, idx) => {
                const t = s.transportation || s.transport;
                if (!t) return null;
                return (
                  <div
                    key={idx}
                    className="border border-[#E4D6A7] bg-white p-4 text-sm"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Truck className="w-4 h-4 text-[#1B3A2B]" />
                      <span className="text-xs font-medium uppercase tracking-wide text-[#1B3A2B]">
                        {s.farmerName || t.vehicle?.name}
                      </span>
                    </div>
                    <p className="text-xs text-[#8A8468]">
                      {t.origin_address} → {t.destination_address} · {t.distance_display}
                    </p>
                    <p className="text-xs text-[#1B3A2B] mt-2 font-medium">
                      Estimated arrival: {t.estimated_arrival_display ?? t.estimatedArrivalDisplay}
                    </p>
                  </div>
                );
              })}
            </div>
          )}

          <button
            onClick={() => {
              setOrderPlaced(null);
              onBack();
            }}
            className="mt-8 mx-auto block px-4 py-2 text-sm border border-[#1B3A2B] text-[#1B3A2B] hover:bg-[#1B3A2B] hover:text-[#F3ECDD] transition-colors"
          >
            Back to shopping
          </button>
        </div>
      </main>
    );
  }

  // ---- Cart listing (main) ------------------------------------------------
  return (
    <main className="max-w-3xl mx-auto px-5 py-10">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[#5C5842] hover:text-[#1B3A2B] transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Continue shopping
      </button>

      <div className="flex items-center gap-2 mt-6 mb-6">
        <ShoppingCart className="w-5 h-5 text-[#1B3A2B]" />
        <h1 className="ff-display text-3xl">Your order</h1>
      </div>

      {cartLines.length === 0 ? (
        <div className="border border-[#E4D6A7] bg-[#FBF7EC] px-6 py-16 text-center">
          <p className="text-sm text-[#5C5842]">
            Nothing added yet — head back to the catalogue to start an order.
          </p>
          <button
            onClick={onBack}
            className="mt-4 px-4 py-2 text-sm border border-[#1B3A2B] text-[#1B3A2B] hover:bg-[#1B3A2B] hover:text-[#F3ECDD] transition-colors"
          >
            Browse products
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="space-y-4">
            {cartLines.map(({ product, qty }) => (
              <div
                key={product.id}
                className="flex items-start gap-3 text-sm border border-[#E4D6A7] bg-[#FBF7EC] p-3"
              >
                <ProductPhoto
                  product={product}
                  className="w-16 h-16 object-cover shrink-0"
                />
                <div className="flex-1">
                  <p className="ff-display text-base leading-tight">{product.name}</p>
                  <p className="text-xs text-[#5C5842] mt-1">{product.farmer}</p>
                  <p className="text-xs text-[#5C5842] tabular mt-1">
                    {qty} {product.unit} × {money(priceFor(product))}
                  </p>
                  {isBusiness && (
                    <p className="text-[11px] text-[#8A6D1E] mt-0.5">
                      Min order {product.minBulkQty} {product.unit}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setQty(product, qty - (isBusiness ? 5 : 1))}
                    className="w-7 h-7 flex items-center justify-center border border-[#D8CBA1] hover:border-[#1B3A2B] active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                  >
                    <Minus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setQty(product, qty + (isBusiness ? 5 : 1))}
                    className="w-7 h-7 flex items-center justify-center border border-[#D8CBA1] hover:border-[#1B3A2B] active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => removeFromCart(product.id)}
                    className="w-7 h-7 flex items-center justify-center text-[#8C2E33] hover:text-[#6B1E2B]"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Order summary */}
          <div className="border border-[#E4D6A7] bg-[#FBF7EC] p-4">
            <h2 className="ff-display text-lg mb-3 flex items-center gap-2">
              <Package className="w-4 h-4 text-[#1B3A2B]" /> Summary
            </h2>
            <div className="text-sm space-y-1">
              {(() => {
                // Prefer authoritative server totals when available
                const t = transport?.totals;
                const s = bizUnlockedSavings;
                if (t && !transportLoading && !transportError) {
                  return (
                    <>
                      <div className="flex justify-between tabular">
                        <span className="text-[#5C5842]">Products</span>
                        <span>{money(t.productSubtotal)}</span>
                      </div>
                      <div className="flex justify-between tabular">
                        <span className="text-[#5C5842] flex items-center gap-1">
                          <Truck className="w-3 h-3" /> Transportation
                        </span>
                        <span>{money(t.transportationTotal)}</span>
                      </div>
                      {s && (
                        <div className="flex justify-between tabular text-[#1B3A2B]">
                          <span>Business savings</span>
                          <span>− {money(savings)}</span>
                        </div>
                      )}
                      <div className="border-t border-[#E4D6A7] my-2" />
                      <div className="flex justify-between tabular font-medium text-[#1B3A2B]">
                        <span>Order Total</span>
                        <span>{money(t.grandTotal)}</span>
                      </div>
                    </>
                  );
                }
                // Fallback while transport loads/errors
                return (
                  <>
                    <div className="flex justify-between tabular">
                      <span className="text-[#5C5842]">Subtotal</span>
                      <span>{money(subtotal)}</span>
                    </div>
                    {s && (
                      <div className="flex justify-between tabular text-[#1B3A2B]">
                        <span>Business savings</span>
                        <span>− {money(savings)}</span>
                      </div>
                    )}
                    {!transportLoading && !transportError && hasLines && (
                      <p className="text-xs text-[#8A8468] pt-1">
                        Fresh delivery quote is being calculated…
                      </p>
                    )}
                  </>
                );
              })()}
            </div>

            <div className="flex items-center gap-1.5 text-xs text-[#5C5842] pt-2">
              <Truck className="w-3.5 h-3.5" />
              {isBusiness ? "Freight quoted at checkout for bulk orders" : "Delivered within 2 days"}
            </div>

            {orderError && (
              <div className="mt-3 border border-[#F0A5A5] bg-[#FFF5F5] px-3 py-2 text-xs text-[#C4544A]">
                {orderError}
              </div>
            )}

            <button
              onClick={handlePlaceOrder}
              disabled={placingOrder || !!transportError}
              title={transportError ? "Fix the delivery issue before placing the order" : undefined}
              className="w-full mt-4 py-2.5 bg-[#1B3A2B] text-[#F3ECDD] text-sm hover:bg-[#14140F] active:bg-[#0E1F17] transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {placingOrder ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Placing order…
                </>
              ) : (
                "Proceed to checkout"
              )}
            </button>

            <p className="text-[11px] text-center text-[#8A8468] mt-2">
              Price and delivery are revalidated with the server before your order is confirmed.
            </p>
          </div>

          {/* Delivery & Transportation (per-shipment breakdown) */}
          <section>
            <h2 className="ff-display text-lg mb-3 flex items-center gap-2">
              <Truck className="w-4 h-4 text-[#1B3A2B]" />
              Delivery & Transportation
            </h2>

            {transportLoading && <TransportLoadingState />}

            {!transportLoading && transportError && (
              <TransportErrorState message={transportError} onRetry={fetchPreview} />
            )}

            {!transportLoading && !transportError && transport?.shipments && (
              <div className="space-y-4">
                {transport.shipments.length > 1 && (
                  <p className="text-xs text-[#5C5842]">
                    Your cart has products from {transport.shipments.length} farmers — quoted separately per pickup location.
                  </p>
                )}
                {transport.shipments.map((shipment, idx) => (
                  <TransportBreakdown key={`${shipment.farmerId || idx}`} shipment={shipment} />
                ))}

                {/* Grand pricing footer (separate from Transportation Service boundary) */}
                <div className="border border-[#E4D6A7] bg-[#FBF7EC] p-4 text-sm">
                  <h3 className="text-xs font-medium uppercase tracking-wide text-[#8A8468] mb-2">
                    Pricing Overview
                  </h3>
                  <div className="space-y-1 tabular">
                    <div className="flex justify-between">
                      <span className="text-[#5C5842]">Products</span>
                      <span>{money(transport.totals?.productSubtotal ?? subtotal)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#5C5842]">Transportation</span>
                      <span>{money(transport.totals?.transportationTotal ?? 0)}</span>
                    </div>
                    <div className="border-t border-[#E4D6A7] my-2" />
                    <div className="flex justify-between font-medium text-[#1B3A2B]">
                      <span>Final Buyer Price</span>
                      <span>{money(transport.totals?.grandTotal ?? subtotal)}</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-[#8A8468] mt-3 leading-relaxed">
                    Product prices (incl. platform fee and farmer floor) are authoritative from the marketplace pricing logic.
                    Transportation cost is calculated by the Transportation Service and shown separately.
                  </p>
                </div>
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}