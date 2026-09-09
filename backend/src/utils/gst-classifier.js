/**
 * Pure GST verification classification helpers.
 * Simplified: format validation + developer demo GSTIN constant.
 * No Sandbox API classification - feature disabled.
 */

export const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
export const DEMO_DEVELOPER_GSTIN = "07AAAAA0000A1Z5";

export const VERIFICATION_DISABLED_MSG =
  "GST verification is currently disabled.";

export function normalizeGstin(gstin) {
  return typeof gstin === "string" ? gstin.trim().toUpperCase() : "";
}

export function isValidGstinFormat(gstin) {
  return GSTIN_REGEX.test(normalizeGstin(gstin));
}

export function notVerifiedResult() {
  return {
    status: "NOT_VERIFIED",
    data: null,
    message: "GST verification is not configured. Only developer demo is available.",
  };
}

export function verificationDisabledResult() {
  return {
    status: "VERIFICATION_DISABLED",
    data: null,
    message: VERIFICATION_DISABLED_MSG,
  };
}

export function formatInvalidResult(message) {
  return {
    status: "FORMAT_INVALID",
    data: null,
    message,
  };
}