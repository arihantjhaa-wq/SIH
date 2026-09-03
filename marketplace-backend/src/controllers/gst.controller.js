import { ApiResponse } from "../utils/api-responce.js";
import { asyncHandler } from "../utils/async-handler.js";
import jwt from "jsonwebtoken";
import { User } from "../models/user.model.js";

const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
const DEMO_DEVELOPER_GSTIN = "07AAAAA0000A1Z5";

/**
 * Checks if the incoming request is from an authenticated developer session.
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
  } catch (err) {
    return null;
  }
}

/**
 * Verify GSTIN using Sandbox.co.in GST API
 * POST /api/v1/gst/verify
 */
export const verifyGstin = asyncHandler(async (req, res) => {
  const { gstin } = req.body;

  // 1. Check if GST Verification is enabled
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

  // 2. Format & Sanitize GSTIN
  if (!gstin || typeof gstin !== "string") {
    return res.status(200).json(
      new ApiResponse(
        200,
        {
          status: "FORMAT_INVALID",
          message: "Please enter a valid 15-character GSTIN.",
        },
        "Invalid GSTIN format"
      )
    );
  }

  const cleanGstin = gstin.trim().toUpperCase();

  // 3. Structural Validation (Standard 15-char Indian GSTIN format)
  if (!GSTIN_REGEX.test(cleanGstin)) {
    return res.status(200).json(
      new ApiResponse(
        200,
        {
          status: "FORMAT_INVALID",
          message: "Invalid GSTIN format. Must be 15 alphanumeric characters (e.g. 27AAACW7823G1ZV).",
        },
        "Invalid GSTIN format"
      )
    );
  }

  // 4. Developer Demo Access Path
  // Check if authenticated caller is a verified developer
  const currentUser = await getAuthenticatedUser(req);
  const isDeveloper = currentUser && currentUser.username === "__developer__";

  if (isDeveloper && (cleanGstin === DEMO_DEVELOPER_GSTIN || req.body.isDemoRequest)) {
    console.log(`[GST] Developer demo verification granted for ${cleanGstin} at ${new Date().toISOString()}`);
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

  // 5. Check Sandbox credentials configuration
  const apiKey = process.env.SANDBOX_API_KEY;
  const authToken = process.env.SANDBOX_AUTH_TOKEN;

  if (!apiKey || !authToken) {
    console.warn(`[GST] Sandbox API credentials missing in environment at ${new Date().toISOString()}`);
    return res.status(200).json(
      new ApiResponse(
        200,
        {
          status: "PROVIDER_UNAVAILABLE",
          message: "GST verification service is temporarily unavailable. Please try again later.",
        },
        "Provider unavailable"
      )
    );
  }

  // 6. Call Sandbox GSTIN Verification API
  const sandboxUrl = `https://api.sandbox.co.in/gsp/public/gstin/${encodeURIComponent(cleanGstin)}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout

  try {
    const response = await fetch(sandboxUrl, {
      method: "GET",
      headers: {
        "x-api-key": apiKey,
        "Authorization": authToken.startsWith("Bearer ") ? authToken : authToken,
        "x-api-version": "1.0",
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const responseData = await response.json().catch(() => null);

    if (response.ok && responseData?.data) {
      const gspData = responseData.data;
      const legalName = gspData.legal_name || gspData.trade_name || "Registered Taxpayer";
      const tradeName = gspData.trade_name || gspData.legal_name || "Business Enterprise";
      const gstinStatus = gspData.status || "Active";
      const taxpayerType = gspData.taxpayer_type || "Regular";

      console.log(`[GST] GSTIN ${cleanGstin} verified successfully via Sandbox at ${new Date().toISOString()}`);

      return res.status(200).json(
        new ApiResponse(
          200,
          {
            status: "VERIFIED",
            data: {
              gstin: cleanGstin,
              legalName,
              tradeName,
              gstinStatus,
              taxpayerType,
              isDemo: false,
            },
            message: "GSTIN verified successfully.",
          },
          "GSTIN verified"
        )
      );
    } else if (response.status === 404 || response.status === 400 || (responseData && responseData.code === 404)) {
      console.warn(`[GST] GSTIN ${cleanGstin} not found in GST portal (Status ${response.status}) at ${new Date().toISOString()}`);
      return res.status(200).json(
        new ApiResponse(
          200,
          {
            status: "NOT_VERIFIED",
            message: "GSTIN not found or inactive with tax authority.",
          },
          "GSTIN not verified"
        )
      );
    } else {
      console.warn(`[GST] Sandbox provider returned status ${response.status} at ${new Date().toISOString()}`);
      return res.status(200).json(
        new ApiResponse(
          200,
          {
            status: "PROVIDER_UNAVAILABLE",
            message: "GST verification service is temporarily unavailable. Please try again later.",
          },
          "Provider unavailable"
        )
      );
    }
  } catch (error) {
    clearTimeout(timeoutId);
    console.error(`[GST] Error calling Sandbox API: ${error.message} at ${new Date().toISOString()}`);

    return res.status(200).json(
      new ApiResponse(
        200,
        {
          status: "PROVIDER_UNAVAILABLE",
          message: "GST verification service is temporarily unavailable. Please try again later.",
        },
        "Provider unavailable"
      )
    );
  }
});
