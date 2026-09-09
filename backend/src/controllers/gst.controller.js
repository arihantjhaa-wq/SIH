import { ApiResponse } from "../utils/api-responce.js";
import { asyncHandler } from "../utils/async-handler.js";
import jwt from "jsonwebtoken";
import { User } from "../models/user.model.js";
import {
  DEMO_DEVELOPER_GSTIN,
  VERIFICATION_DISABLED_MSG,
  isValidGstinFormat,
  normalizeGstin,
  verificationDisabledResult,
  notVerifiedResult,
  formatInvalidResult,
} from "../utils/gst-classifier.js";

/**
 * Resolves the authenticated user for a request, or null when unauthenticated.
 */
async function getAuthenticatedUser(req) {
  try {
    const token =
      req.cookies?.accessToken ||
      req.header("Authorization")?.replace("Bearer ", "");

    if (!token) return null;

    const decodedToken = jwt.verify(token, process.env.ACCESS_TOKEN_SECRET);
    if (!decodedToken?._id) return null;

    const user = await User.findById(decodedToken._id).select("username email");
    return user;
  } catch {
    return null;
  }
}

/**
 * Verify GSTIN
 * POST /api/v1/gst/verify
 *
 * Behavior:
 * - If GST_VERIFICATION_ENABLED !== "true" → VERIFICATION_DISABLED
 * - If GSTIN format invalid → FORMAT_INVALID
 * - If GSTIN == DEMO_DEVELOPER_GSTIN AND user is authenticated (any user) → VERIFIED (isDemo: true)
 * - Otherwise → NOT_VERIFIED (real API verification disabled)
 */
export const verifyGstin = asyncHandler(async (req, res) => {
  const { gstin } = req.body;

  // 1. Is verification enabled by configuration?
  if (process.env.GST_VERIFICATION_ENABLED !== "true") {
    return res.status(200).json(
      new ApiResponse(
        200,
        verificationDisabledResult(),
        "GST verification is disabled"
      )
    );
  }

  // 2. Format & sanitize input
  if (typeof gstin !== "string" || !gstin.trim()) {
    return res
      .status(200)
      .json(
        new ApiResponse(
          200,
          formatInvalidResult("Please enter a valid 15-character GSTIN."),
          "Invalid GSTIN format"
        )
      );
  }

  const cleanGstin = normalizeGstin(gstin);

  // 3. Local structural validation
  if (!isValidGstinFormat(cleanGstin)) {
    return res
      .status(200)
      .json(
        new ApiResponse(
          200,
          formatInvalidResult(
            "Invalid GSTIN format. Must be 15 alphanumeric characters (e.g. 27AAACW7823G1ZV)."
          ),
          "Invalid GSTIN format"
        )
      );
  }

  // 4. Developer demo path — works for ANY authenticated user (not just __developer__)
  const currentUser = await getAuthenticatedUser(req);
  const isAuthenticated = Boolean(currentUser);

  if (cleanGstin === DEMO_DEVELOPER_GSTIN) {
    if (isAuthenticated) {
      console.log(
        `[GST] Developer demo verification granted for user ${currentUser?.username} at ${new Date().toISOString()}`
      );
      return res.status(200).json(
        new ApiResponse(
          200,
          {
            status: "VERIFIED",
            data: {
              gstin: cleanGstin,
              legalName: "AgriDirect Developer Demo Enterprise",
              tradeName: "AgriDirect Demo Agro Supplies",
              gstinStatus: "Active",
              taxpayerType: "Regular",
              isDemo: true,
            },
            message: "Developer demo GSTIN verified successfully.",
          },
          "GSTIN verified (Developer Demo)"
        )
      );
    }

    // Unauthenticated user cannot use the demo GSTIN
    console.warn(
      `[GST] Unauthenticated user attempted demo GSTIN ${cleanGstin} at ${new Date().toISOString()}`
    );
    return res.status(200).json(
      new ApiResponse(
        200,
        notVerifiedResult(),
        "GSTIN not verified"
      )
    );
  }

  // 5. Real GSTIN verification - feature disabled, return NOT_VERIFIED
  return res.status(200).json(
    new ApiResponse(
      200,
      notVerifiedResult(),
      "GSTIN not verified"
    )
  );
});