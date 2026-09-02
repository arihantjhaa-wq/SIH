import { Router } from "express";

const router = Router();


import { healthCheack } from "../controllers/healthcheack.controller.js";
router.route("/").get(healthCheack);


export default router;