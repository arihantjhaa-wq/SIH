import { Router } from "express";
import { verifyGstin } from "../controllers/gst.controller.js";

const router = Router();

// GSTIN Verification
router.route("/verify").post(verifyGstin);

export default router;
