import { Product } from "../models/product.model.js";
import { User } from "../models/user.model.js";
import { ApiError } from "./api-error.js";

// ---------------------------------------------------------------------------
// Transportation Service integration
//
// The Marketplace Backend is the only component that talks to the
// Transportation Service (port 8001). It supplies ALL of the trusted data:
//   - origin      → farmer's registered address (resolved server-side from
//                   product → addedBy → User.address)
//   - destination → consumer's registered address (resolved server-side from
//                   the authenticated consumer JWT)
//   - quantity    → server-computed kg from cart quantities
//   - departure   → server timestamp (never client time)
//
// The React frontend never receives the Google Maps API key and never sends
// an arbitrary origin/destination/vehicle/departure.
// ---------------------------------------------------------------------------

const TRANSPORT_SERVICE_URL =
  process.env.TRANSPORTATION_SERVICE_URL || "http://localhost:8001";

const TRANSPORT_SERVICE_TIMEOUT_MS = 20000;

// MVP unit → kg approximations. These are documented estimates used only to
// pick a vehicle. `kg` and `g` are exact; the rest are conservative defaults.
const UNIT_TO_KG = {
  kg: 1,
  g: 0.001,
  litre: 1, // ≈1 kg/litre for produce liquids (documented MVP assumption)
  ml: 0.001,
  dozen: 6, // ≈0.5 kg avg per unit × 12 (documented MVP default)
  piece: 0.5, // ≈0.5 kg avg per piece (documented MVP default)
};

export const UNIT_DISPLAY_SUFFIX = (unit) => (unit === "dozen" ? " dozen" : ` ${unit}`);

export function computeQuantityKg(qty, unit) {
  const factor = UNIT_TO_KG[unit] ?? 1;
  return Number(qty) * factor;
}

export function formatQuantityKg(kg) {
  if (kg >= 1000) return `${(kg / 1000).toFixed(1)}T`;
  if (kg >= 100) return `${Math.round(kg)} kg`;
  if (kg >= 1) return `${kg.toFixed(1)} kg`;
  return `${Math.round(kg * 1000)} g`;
}

/**
 * Call the Transportation Service for a single shipment quote.
 * Errors are logged server-side and returned to the client as a safe,
 * human-readable message (no stack traces, no internal detail).
 */
export async function callTransportService({
  originAddress,
  destinationAddress,
  quantityKg,
  departureDatetime,
}) {
  let res;
  try {
    res = await fetch(`${TRANSPORT_SERVICE_URL}/api/v1/transport/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        origin_address: originAddress,
        destination_address: destinationAddress,
        quantity_kg: Number(quantityKg),
        departure_datetime: departureDatetime,
      }),
      signal: AbortSignal.timeout(TRANSPORT_SERVICE_TIMEOUT_MS),
    });
  } catch (err) {
    console.error("[TRANSPORT] Network error calling transportation service:", err?.message);
    throw new ApiError(
      502,
      "We couldn't calculate the delivery route right now. Please try again in a moment.",
    );
  }

  const json = await res.json().catch(() => ({}));

  if (!res.ok) {
    const detail = json?.detail || json?.message || `HTTP ${res.status}`;
    console.error(`[TRANSPORT] Service returned ${res.status}:`, detail);
    // Errors beyond our control (Google outage, service down) → friendly 502.
    // Quantity / capacity problems → the message is already human-readable.
    if (res.status === 422) {
      throw new ApiError(422, normalizeTransportMessage(detail));
    }
    throw new ApiError(
      502,
      "We couldn't calculate the delivery route right now. Please try again in a moment.",
    );
  }

  return json;
}

// Keep the user-facing text tidy for known service messages, fall back to a
// generic friendly line for anything else.
function normalizeTransportMessage(detail) {
  const text = typeof detail === "string" ? detail : String(detail || "");
  if (/capacity|exceeds|split/i.test(text)) {
    return "This order is too large for a single delivery vehicle. Please split it into smaller shipments.";
  }
  if (/invalid|quantity/i.test(text)) {
    return "The order quantity looks invalid. Please check your cart and try again.";
  }
  return "We couldn't calculate the delivery route right now. Please try again in a moment.";
}

/**
 * Resolve the authenticated consumer's cart into per-farmer shipments.
 *
 * Each shipment represents ONE origin location (one farmer). Products from
 * different farmers are NEVER merged into a single origin — the MVP quotes
 * one independent trip per farmer.
 *
 * Returns:
 *   {
 *     consumerAddress, serverTimestamp,
 *     shipments: [{
 *        farmerId?, farmerName, originAddress, destinationAddress,
 *        quantityKg, quantityDisplay,
 *        productLines: [{ productId, name, unit, qty, unitPrice, amount, priceTier }],
 *        productAmount,
 *     }]
 *   }
 */
export async function resolveShipments(items, consumerId, priceTier = "individual") {
  if (!items || !Array.isArray(items) || items.length === 0) {
    throw new ApiError(400, "Your cart is empty");
  }

  const consumer = await User.findById(consumerId);
  if (!consumer) {
    throw new ApiError(401, "Authentication required");
  }
  if (!consumer.address || !consumer.address.trim()) {
    throw new ApiError(
      400,
      "Please add your delivery address to your profile before checking out.",
    );
  }

  const productIds = items.map((i) => i.productId);
  const products = await Product.find({ _id: { $in: productIds } });
  const productMap = new Map(products.map((p) => [String(p._id), p]));

  // Load every farmer that owns an ordered product
  const farmerIds = [
    ...new Set(products.map((p) => p.addedBy).filter(Boolean)),
  ];
  const farmers = await User.find({ _id: { $in: farmerIds } }).select(
    "_id fullName username address email",
  );
  const farmerMap = new Map(farmers.map((f) => [String(f._id), f]));

  // Group ordered lines by farmer
  const groups = new Map();
  const serverTimestamp = new Date();

  for (const { productId, qty } of items) {
    const product = productMap.get(String(productId));
    if (!product) {
      throw new ApiError(
        404,
        "One of the products in your cart is no longer available. Please refresh to update your cart.",
      );
    }

    const numQty = Number(qty);
    if (!Number.isFinite(numQty) || numQty <= 0) {
      throw new ApiError(400, "One of the quantities in your cart is invalid.");
    }

    // Determine the farmer owner. Seed/demo catalogue products have no linked
    // farmer user, so they cannot be shipped automatically in this MVP.
    if (!product.addedBy) {
      throw new ApiError(
        400,
        `"${product.name}" has no linked farmer delivery origin yet, so we can't schedule transport for it.`,
      );
    }

    const farmer = farmerMap.get(String(product.addedBy));
    if (!farmer) {
      throw new ApiError(
        400,
        `The farmer for "${product.name}" is no longer active.`,
      );
    }
    if (!farmer.address || !farmer.address.trim()) {
      throw new ApiError(
        400,
        `The farmer for "${product.name}" hasn't set a pickup address yet, so we can't calculate delivery.`,
      );
    }

    const key = String(farmer._id);
    if (!groups.has(key)) {
      groups.set(key, {
        farmerId: farmer._id,
        farmerName: farmer.fullName || farmer.username || "Farmer",
        originAddress: farmer.address,
        destinationAddress: consumer.address,
        productLines: [],
        quantityKg: 0,
      });
    }
    const group = groups.get(key);

    const unitPrice = priceTier === "business" ? product.bizPrice : product.indivPrice;
    const amount = unitPrice * numQty;

    group.productLines.push({
      productId: String(product._id),
      name: product.name,
      unit: product.unit,
      qty: numQty,
      unitPrice,
      amount: round2(amount),
      priceTier: priceTier === "business" ? "business" : "individual",
    });
    group.quantityKg += computeQuantityKg(numQty, product.unit);
  }

  // Build final shipment list with computed fields
  const shipments = [];
  let productSubtotal = 0;
  for (const group of groups.values()) {
    group.quantityKg = round2(group.quantityKg);
    group.quantityDisplay = formatQuantityKg(group.quantityKg);
    const productAmount = round2(
      group.productLines.reduce((s, l) => s + l.amount, 0),
    );
    group.productAmount = productAmount;
    productSubtotal += productAmount;
    shipments.push(group);
  }

  return {
    consumerAddress: consumer.address,
    serverTimestamp: serverTimestamp.toISOString(),
    shipments,
    productSubtotal: round2(productSubtotal),
    priceTier: priceTier === "business" ? "business" : "individual",
  };
}

/**
 * Fetch fresh transportation quotes for every shipment (used both for the
 * cart preview and — again, freshly — at order creation for revalidation).
 */
export async function quoteAllShipments(resolved) {
  const shipmentsWithTransport = [];
  let transportationTotal = 0;

  for (const shipment of resolved.shipments) {
    const transportation = await callTransportService({
      originAddress: shipment.originAddress,
      destinationAddress: shipment.destinationAddress,
      quantityKg: shipment.quantityKg,
      departureDatetime: resolved.serverTimestamp,
    });

    const transportCost = Number(transportation.total_transportation_cost || 0);
    transportationTotal += transportCost;

    shipmentsWithTransport.push({
      ...shipment,
      shipmentTransportCost: transportCost,
      shipmentTotal: round2(shipment.productAmount + transportCost),
      transportation,
    });
  }

  return {
    ...resolved,
    shipments: shipmentsWithTransport,
    totals: {
      productSubtotal: resolved.productSubtotal,
      transportationTotal: round2(transportationTotal),
      grandTotal: round2(resolved.productSubtotal + transportationTotal),
    },
  };
}

function round2(n) {
  return Math.round((Number(n) + Number.EPSILON) * 100) / 100;
}