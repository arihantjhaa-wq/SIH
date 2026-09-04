import mongoose, { Schema } from "mongoose";

const productSchema = new Schema(
  {
    name: {
      type: String,
      required: true,
      trim: true,
    },
    category: {
      type: String,
      required: true,
      trim: true,
    },
    unit: {
      type: String,
      required: true,
      trim: true,
    },
    photo: {
      type: String,
      default: null,
    },
    imageData: {
      type: String,
      default: null,
    },
    indivPrice: {
      type: Number,
      required: true,
    },
    bizPrice: {
      type: Number,
      required: true,
    },
    minBulkQty: {
      type: Number,
      required: true,
    },
    farmer: {
      type: String,
      required: true,
      trim: true,
    },
    farmerAdded: {
      type: Boolean,
      default: false,
    },
  },
  {
    timestamps: true,
  }
);

export const Product = mongoose.model("Product", productSchema);
