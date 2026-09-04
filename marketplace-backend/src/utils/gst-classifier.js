/**
 * Pure GST verification classification helpers.
 * No DB or network dependencies — safe to unit test in isolation.
 */

export const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
export const DEMO_DEVELOPER_GSTIN = "07AAAAA0000A1Z5";

export const PROVIDER_UNAVAILABLE_MSG =
  "GST verification service is temporarily unavailable. Please try again later.";

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
    message: "GSTIN not found or inactive with tax authority.",
  };
}

export function providerUnavailableResult() {
  return {
    status: "PROVIDER_UNAVAILABLE",
    data: null,
    message: PROVIDER_UNAVAILABLE_MSG,
  };
}

/**
 * Classifies a raw Sandbox verify response into a verification result.
 * Never throws. Handles nested data structures and optional fields safely.
 *
 * @param {{ status:number, ok:boolean, body:any }} response
 */
export function classifySandboxResponse({ status, body }) {
  // HTTP 200 -> parse the actual GSTIN data
  if (status === 200) {
    // Null body on 200 is ambiguous — treat as not verified (provider gave no data)
    if (body === null || body === undefined) {
      return notVerifiedResult();
    }

    // Non-object body (string, number, etc.) indicates a malformed provider response
    if (typeof body !== "object" || Array.isArray(body)) {
      return providerUnavailableResult();
    }

    // Sandbox nests the payload under data.data
    const inner = body?.data?.data ?? body?.data ?? body ?? {};

    // Inner extraction must produce an object to be usable
    if (!inner || typeof inner !== "object" || Array.isArray(inner)) {
      return providerUnavailableResult();
    }

    const gstStatus = (inner.status || "").toLowerCase();
    const validGstin = inner.validGstin;
    const isCancelled =
      gstStatus === "cancelled" ||
      gstStatus === "inactive" ||
      gstStatus === "suspended" ||
      gstStatus === "cancel";

    if (validGstin === false || isCancelled) {
      return notVerifiedResult();
    }

    if (validGstin === true || gstStatus === "active") {
      const legalName =
        inner.legalName ||
        inner.legal_name ||
        inner.tradeName ||
        "Registered Taxpayer";
      const tradeName = inner.tradeName || inner.trade_name || "";
      return {
        status: "VERIFIED",
        data: {
          gstin: inner.gstin || inner.gstinNumber,
          legalName,
          tradeName: tradeName && tradeName !== legalName ? tradeName : "",
          gstinStatus: inner.status || "Active",
          taxpayerType:
            inner.bussNature ||
            inner.businessNature ||
            inner.taxpayerType ||
            "Regular",
          isDemo: false,
        },
        message: "GSTIN verified successfully.",
      };
    }

    // Present but cannot be confirmed as active
    return notVerifiedResult();
  }

  // Sandbox rejected the format / could not find it
  if (status === 422 || status === 404 || status === 400) {
    return notVerifiedResult();
  }

  // Genuine provider problems: rate limit, server errors, unexpected statuses
  if (status === 429 || status >= 500) {
    return providerUnavailableResult();
  }

  return providerUnavailableResult();
}
