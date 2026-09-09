import api from "./api.js";

/**
 * Fetch a transportation preview for the current cart.
 * Called by the cart page BEFORE checkout so the consumer sees
 * where the product comes from, how it will be transported, and
 * when it should arrive — without any manual origin/destination/vehicle inputs.
 */
export async function fetchTransportPreview(cart, priceTier = "individual") {
  const normalizedCart = Object.entries(cart).map(([productId, qty]) => ({
    productId,
    qty,
  }));
  const { data } = await api.post("/orders/preview", {
    cart: normalizedCart,
    priceTier,
  });
  return data.data;
}

/**
 * Create an order with fresh server-side transportation revalidation.
 * The server recomputes transportation from trusted data — the frontend never
 * supplies origin, destination, vehicle, or departure time.
 */
export async function createTransportOrder(cart, priceTier = "individual") {
  const normalizedCart = Object.entries(cart).map(([productId, qty]) => ({
    productId,
    qty,
  }));
  const { data } = await api.post("/orders", {
    cart: normalizedCart,
    priceTier,
  });
  return data.data;
}