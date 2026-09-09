import mongoose, { Schema } from "mongoose";

/**
 * Order — created ONLY on the marketplace backend with the server's
 * authoritative timestamp. Transportation quotes snapshotted at checkout
 * so the final order reflects a fresh server-side calculation.
 */
const orderSchema = new Schema(
  {
    orderNumber: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },
    consumer: {
      type: Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    // Pricing tier is selected by the consumer (individual/business) but the
    // unit prices themselves are ALWAYS read from the product record server-side.
    pricingTier: {
      type: String,
      enum: ["individual", "business"],
      default: "individual",
    },
    items: [
      {
        product: { type: Schema.Types.ObjectId, ref: "Product", required: true },
        name: { type: String, required: true },
        unit: { type: String, required: true },
        qty: { type: Number, required: true },
        unitPrice: { type: Number, required: true },
        amount: { type: Number, required: true },
      },
    ],
    // One shipment per farmer origin. Never merges unrelated origins.
    shipments: [
      {
        farmerId: { type: Schema.Types.ObjectId, ref: "User" },
        farmerName: { type: String },
        originAddress: { type: String },
        destinationAddress: { type: String },
        quantityKg: { type: Number },
        quantityDisplay: { type: String },
        productLines: [
          {
            productId: { type: String },
            name: { type: String },
            unit: { type: String },
            qty: { type: Number },
            unitPrice: { type: Number },
            amount: { type: Number },
            priceTier: { type: String },
          },
        ],
        productAmount: { type: Number },
        shipmentTransportCost: { type: Number },
        shipmentTotal: { type: Number },
        transportation: { type: Schema.Types.Mixed, default: null },
      },
    ],
    orderTimestamp: {
      type: Date,
      required: true,
      default: Date.now, // server-side authoritative creation time
    },
    productSubtotal: { type: Number, required: true },
    transportationTotal: { type: Number, default: 0 },
    grandTotal: { type: Number, required: true },
    status: {
      type: String,
      enum: ["confirmed", "in_transit", "delivered", "cancelled"],
      default: "confirmed",
    },
  },
  { timestamps: true }
);

// A short human-friendly order number: KS-<YYMMDDHHmm>-<rand4>
function generateOrderNumber() {
  const d = new Date();
  const pad = (n, l = 2) => String(n).padStart(l, "0");
  return `KS-${pad(d.getFullYear() % 100)}${pad(d.getMonth() + 1)}${pad(
    d.getDate(),
  )}${pad(d.getHours())}${pad(d.getMinutes())}-${Math.floor(1000 + Math.random() * 9000)}`;
}

orderSchema.pre("validate", function () {
  if (!this.orderNumber) {
    this.orderNumber = generateOrderNumber();
  }
});

orderSchema.pre("save", function () {
  if (!this.orderNumber) {
    this.orderNumber = generateOrderNumber();
  }
});

orderSchema.pre("validate", async function () {
  if (!this.orderNumber) {
    const d = new Date();
    const pad = (n, l = 2) => String(n).padStart(l, "0");
    this.orderNumber = `KS-${pad(d.getFullYear() % 100)}${pad(d.getMonth() + 1)}${pad(
      d.getDate(),
    )}${pad(d.getHours())}${pad(d.getMinutes())}-${Math.floor(1000 + Math.random() * 9000)}`;
  }
});

export const Order = mongoose.model("Order", orderSchema);