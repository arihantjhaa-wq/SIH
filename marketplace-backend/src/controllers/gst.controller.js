import { ApiResponse } from "../utils/api-responce.js";
import { asyncHandler } from "../utils/async-handler.js";
import jwt from "jsonwebtoken";
import { User } from "../models/user.model.js";
import {
  hasSandboxCredentials,
  verifyGstinWithSandbox,
  clearSandboxTokenCache,
} from "../utils/sandbox-client.js";
import {
  DEMO_DEVELOPER_GSTIN,
  PROVIDER_UNAVAILABLE_MSG,
  classifySandboxResponse,
  isValidGstinFormat,
} from "../utils/gst-classifier.js";

/**
 * Resolves the authenticated user for a request, or null when unauthenticated.
 * Used to independently verify a developer session on the server.
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

function formatInvalid(message) {
  return new ApiResponse(
    200,
    { status: "FORMAT_INVALID", data: null, message },
    "Invalid GSTIN format"
  );
}

function notVerified() {
  return new ApiResponse(
    200,
    {
      status: "NOT_VERIFIED",
      data: null,
      message: "GSTIN not found or inactive with tax authority.",
    },
    "GSTIN not verified"
  );
}

function providerUnavailable() {
  return new ApiResponse(
    200,
    { status: "PROVIDER_UNAVAILABLE", data: null, message: PROVIDER_UNAVAILABLE_MSG },
    "Provider unavailable"
  );
}


/**
 * Verify GSTIN using Sandbox.co.in GST API
 * POST /api/v1/gst/verify
 */
export const verifyGstin = asyncHandler(async (req, res) => {
  const { gstin } = req.body;

  // 1. Is verification enabled by configuration?
  if (process.env.GST_VERIFICATION_ENABLED !== "true") {
    return res.status(200).json(
      new ApiResponse(
        200,
        {
          status: "VERIFICATION_DISABLED",
          message: "GST verification is currently disabled.",
        },
        "GST verification is disabled"
      )
    );
  }

  // 2. Format & sanitize input
  if (typeof gstin !== "string" || !gstin.trim()) {
    return res
      .status(200)
      .json(formatInvalid("Please enter a valid 15-character GSTIN."));
  }

  const cleanGstin = gstin.trim().toUpperCase();

  // 3. Local structural validation — bad format never reaches Sandbox
  if (!isValidGstinFormat(cleanGstin)) {
    return res
      .status(200)
      .json(
        formatInvalid(
          "Invalid GSTIN format. Must be 15 alphanumeric characters (e.g. 27AAACW7823G1ZV)."
        )
      );
  }

  // 4. Developer demo path — server independently verifies the authenticated
  //    developer session. isDemoRequest alone grants nothing.
  const currentUser = await getAuthenticatedUser(req);
  const isDeveloper = Boolean(
    currentUser && currentUser.username === "__developer__"
  );

  if (cleanGstin === DEMO_DEVELOPER_GSTIN) {
    if (isDeveloper) {
      console.log(
        `[GST] Developer demo verification granted at ${new Date().toISOString()}`
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

    // Non-developer cannot use the demo GSTIN, and the demo GSTIN is never
    // sent to Sandbox.
    console.warn(
      `[GST] Non-developer attempted demo GSTIN ${cleanGstin} at ${new Date().toISOString()}`
    );
    return res.status(200).json(notVerified());
  }

  // 5. Sandbox credentials must be configured
  if (!hasSandboxCredentials()) {
    console.warn(
      `[GST] Sandbox API credentials missing in environment at ${new Date().toISOString()}`
    );
    return res.status(200).json(providerUnavailable());
  }

  // 6. Call the current Sandbox Verify GSTIN API
  try {
    let result = await verifyGstinWithSandbox(cleanGstin);

    // 401/403 -> the cached access token likely expired. Clear and retry once
    // with a freshly minted token before declaring the provider unavailable.
    if (result.status === 401 || result.status === 403) {
      console.warn(
        `[GST] Sandbox auth rejected (HTTP ${result.status}); refreshing token at ${new Date().toISOString()}`
      );
      clearSandboxTokenCache();
      try {
        result = await verifyGstinWithSandbox(cleanGstin);
      } catch {
        return res.status(200).json(providerUnavailable());
      }
    }

    const classification = classifySandboxResponse(result);
    return res.status(200).json(
      new ApiResponse(200, classification, classification.status === "VERIFIED" ? "GSTIN verified" : "GSTIN verification result")
    );
  } catch (err) {
    // Network / DNS / timeout / authentication / configuration failure
    console.warn(
      `[GST] Sandbox call failed (${err.code || "unknown"}): ${err.message} at ${new Date().toISOString()}`
    );
    return res.status(200).json(providerUnavailable());
  }
});
