import { Order } from "../models/order.model.js";
import { ApiResponse } from "../utils/api-responce.js";
import { ApiError } from "../utils/api-error.js";
import { asyncHandler } from "../utils/async-handler.js";
import {
  resolveShipments,
  quoteAllShipments,
} from "../utils/transportation.js";

// ---------------------------------------------------------------------------
// GET /api/v1/orders/preview
//
// Returns a fresh transportation calculation for the current cart contents.
// Does NOT create an order — used by the cart page to show delivery info.
// ---------------------------------------------------------------------------
const previewTransport = asyncHandler(async (req, res) => {
  const user = req.user;
  const { cart, priceTier = "individual" } = req.body;

  if (!cart || !Array.isArray(cart) || cart.length === 0) {
    throw new ApiError(400, "Cart is empty");
  }

  const items = cart.map(({ productId, qty }) => ({ productId, qty }));

  const resolved = await resolveShipments(items, user._id, priceTier);
  const quoted = await quoteAllShipments(resolved);

  return res
    .status(200)
    .json(
      new ApiResponse(
        200,
        quoted,
        "Transportation preview calculated successfully",
      ),
    );
});

// ---------------------------------------------------------------------------
// POST /api/v1/orders
//
// Creates an order with FRESH transportation quotes revalidated at checkout.
// The server timestamp is authoritative. The client MUST send its current
// cart (productId + qty) and pricingTier so the backend can recalculate.
// ---------------------------------------------------------------------------
const createOrder = asyncHandler(async (req, res) => {
  const user = req.user;
  const { cart, priceTier = "individual" } = req.body;

  if (!cart || !Array.isArray(cart) || cart.length === 0) {
    throw new ApiError(400, "Cart is empty");
  }

  const items = cart.map(({ productId, qty }) => ({ productId, qty }));

  // Fresh server-side revalidation
  const resolved = await resolveShipments(items, user._id, priceTier);
  const quoted = await quoteAllShipments(resolved);

  // Persist order with snapped transportation data
  const order = await Order.create({
    consumer: user._id,
    pricingTier: priceTier === "business" ? "business" : "individual",
    items: quoted.shipments.flatMap((s) =>
      s.productLines.map((l) => ({
        product: l.productId,
        name: l.name,
        unit: l.unit,
        qty: l.qty,
        unitPrice: l.unitPrice,
        amount: l.amount,
      })),
    ),
    shipments: quoted.shipments.map((s) => ({
      farmerId: s.farmerId,
      farmerName: s.farmerName,
      originAddress: s.originAddress,
      destinationAddress: s.destinationAddress,
      quantityKg: s.quantityKg,
      quantityDisplay: s.quantityDisplay,
      productLines: s.productLines,
      productAmount: s.productAmount,
      shipmentTransportCost: s.shipmentTransportCost,
      shipmentTotal: s.shipmentTotal,
      transportation: s.transportation,
    })),
    orderTimestamp: new Date(), // authoritative server timestamp
    productSubtotal: quoted.totals.productSubtotal,
    transportationTotal: quoted.totals.transportationTotal,
    grandTotal: quoted.totals.grandTotal,
    status: "confirmed",
  });

  return res
    .status(201)
    .json(
      new ApiResponse(
        201,
        { order },
        "Order placed successfully",
      ),
    );
});

// ---------------------------------------------------------------------------
// GET /api/v1/orders/mine
//
// Authenticated consumer's own order history.
// ---------------------------------------------------------------------------
const getMyOrders = asyncHandler(async (req, res) => {
  const orders = await Order.find({ consumer: req.user._id })
    .sort({ createdAt: -1 })
    .populate("items.product", "name unit photo")
    .lean();

  return res
    .status(200)
    .json(
      new ApiResponse(
        200,
        orders,
        "Your orders fetched successfully",
      ),
    );
});

// ---------------------------------------------------------------------------
// GET /api/v1/orders/:id
//
// Single order detail (consumer or developer only).
// ---------------------------------------------------------------------------
const getOrderById = asyncHandler(async (req, res) => {
  const { id } = req.params;
  const order = await Order.findById(id).lean();

  if (!order) {
    throw new ApiError(404, "Order not found");
  }

  // Authorization: order must belong to the authenticated consumer,
  // or the user must be a developer/admin.
  if (
    String(order.consumer) !== String(req.user._id) &&
    !req.user.isDeveloper
  ) {
    throw new ApiError(404, "Order not found");
  }

  return res
    .status(200)
    .json(
      new ApiResponse(
        200,
        { order },
        "Order fetched successfully",
      ),
    );
});

export {
  previewTransport,
  createOrder,
  getMyOrders,
  getOrderById,
};