import { Router } from "express";
import { verifyJWT } from "../middlewares/auth.middleware.js";
import {
  getProducts,
  getProductById,
  getMyProducts,
  getAdminProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  seedProducts,
} from "../controllers/product.controller.js";

const router = Router();

// Public (seeded products for marketplace browsing)
router.route("/").get(getProducts);

// Public: seed products
router.route("/seed").post(seedProducts);

// Authenticated farmer: own products
router.route("/mine").get(verifyJWT, getMyProducts);

// Developer/Admin: all products with ownership info
router.route("/admin").get(verifyJWT, getAdminProducts);

// Authenticated farmer: create product
router.route("/").post(verifyJWT, createProduct);

// Parameterized routes MUST come after specific routes
router.route("/:id").get(getProductById);

// Authenticated farmer/developer: update product
router.route("/:id").put(verifyJWT, updateProduct);

// Authenticated farmer/developer: delete product
router.route("/:id").delete(verifyJWT, deleteProduct);

export default router;