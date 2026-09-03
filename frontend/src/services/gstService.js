import api from "./api.js";

/**
 * Verify GSTIN with backend API (which calls Sandbox.co.in GST verification)
 * @param {string} gstin - The GSTIN to verify
 * @param {boolean} isDemoRequest - Optional flag to request developer demo verification
 * @returns {Promise} Response with status: VERIFIED, NOT_VERIFIED, FORMAT_INVALID, PROVIDER_UNAVAILABLE, or VERIFICATION_DISABLED
 */
export async function verifyGstinApi({ gstin, isDemoRequest = false }) {
  const { data } = await api.post("/gst/verify", { gstin, isDemoRequest });
  return data.data;
}
