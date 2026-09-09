import { Router } from "express";
import { verifyJWT } from "../middlewares/auth.middleware.js";
import {
  previewTransport,
  createOrder,
  getMyOrders,
  getOrderById,
} from "../controllers/order.controller.js";

const router = Router();

// All order routes require authentication
router.use(verifyJWT);

// POST /api/v1/orders/preview — fresh transportation preview for current cart
router.route("/preview").post(previewTransport);

// POST /api/v1/orders — create order (with fresh server-side transport revalidation)
router.route("/").post(createOrder);

// GET /api/v1/orders/mine — authenticated consumer's order history
router.route("/mine").get(getMyOrders);

// GET /api/v1/orders/:id — single order detail
router.route("/:id").get(getOrderById);

export default router;