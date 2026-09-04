import { Router } from "express";
import {
  getProducts,
  getProductById,
  createProduct,
  deleteProduct,
  seedProducts,
} from "../controllers/product.controller.js";

const router = Router();

router.route("/").get(getProducts);
router.route("/seed").post(seedProducts);
router.route("/:id").get(getProductById);
router.route("/").post(createProduct);
router.route("/:id").delete(deleteProduct);

export default router;
