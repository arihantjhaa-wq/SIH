/**
 * Sandbox.co.in API client (server-side only).
 *
 * Handles:
 *   - Authentication: exchanges the Sandbox API key + API secret for a JWT
 *     access token via the Authenticate API. The access token is valid for
 *     24 hours and is cached in-memory, then regenerated automatically when
 *     it expires or is rejected by the provider.
 *   - GSTIN verification: calls the current Sandbox Verify GSTIN API
 *     (POST /gst/compliance/public/gstin/verify).
 *
 * Security:
 *   - API key, API secret and access token NEVER leave the server.
 *   - They are never sent to the React client, never put in frontend env vars,
 *     and never logged.
 */

// In-memory token cache (per process)
let cachedAccessToken = null;
let cachedTokenExpiry = 0;

const TOKEN_TTL_MS = 24 * 60 * 60 * 1000; // Sandbox tokens valid 24h
const TOKEN_BUFFER_MS = 5 * 60 * 1000; // refresh 5 min before hard expiry
const DEFAULT_TIMEOUT_MS = 10000;

const API_BASE = "https://api.sandbox.co.in";

/**
 * Reads Sandbox credentials from the environment.
 * Prefers SANDBOX_API_SECRET when present; otherwise falls back to the
 * legacy SANDBOX_AUTH_TOKEN (which has historically carried the API secret).
 * Returns only booleans/lengths for logging — never the values.
 */
export function sandboxConfig() {
  const apiKey = process.env.SANDBOX_API_KEY;
  const apiSecret = process.env.SANDBOX_API_SECRET || process.env.SANDBOX_AUTH_TOKEN;
  return { apiKey, apiSecret };
}

/**
 * True when Sandbox credentials are configured (without exposing them).
 */
export function hasSandboxCredentials() {
  const { apiKey, apiSecret } = sandboxConfig();
  return Boolean(apiKey && apiSecret);
}

/**
 * Clears the cached access token (used for forced refresh and tests).
 */
export function clearSandboxTokenCache() {
  cachedAccessToken = null;
  cachedTokenExpiry = 0;
}

function withTimeout(fetchImpl, url, options, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  return fetchImpl(url, { ...options, signal: controller.signal }).finally(() => {
    clearTimeout(timeoutId);
  });
}

/**
 * Obtain (or reuse) a Sandbox access token via the Authenticate API.
 * @param {typeof fetch} [fetchImpl] injectable for tests
 */
export async function getSandboxAccessToken(fetchImpl = fetch) {
  if (cachedAccessToken && Date.now() < cachedTokenExpiry) {
    return cachedAccessToken;
  }

  const { apiKey, apiSecret } = sandboxConfig();
  if (!apiKey || !apiSecret) {
    const err = new Error("Sandbox API credentials are not configured");
    err.code = "SANDBOX_CONFIG_ERROR";
    throw err;
  }

  let response;
  try {
    response = await withTimeout(
      fetchImpl,
      `${API_BASE}/authenticate`,
      {
        method: "POST",
        headers: {
          "x-api-key": apiKey,
          "x-api-secret": apiSecret,
          "x-api-version": "1.0",
        },
      },
    );
  } catch (err) {
    const e = new Error("Sandbox authenticate request failed");
    e.code = "SANDBOX_AUTH_FAILED";
    e.cause = err;
    throw e;
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok || !body?.data?.access_token) {
    const e = new Error(`Sandbox authenticate failed (HTTP ${response.status})`);
    e.code = "SANDBOX_AUTH_FAILED";
    e.status = response.status;
    throw e;
  }

  cachedAccessToken = body.data.access_token;
  cachedTokenExpiry = Date.now() + (TOKEN_TTL_MS - TOKEN_BUFFER_MS);
  return cachedAccessToken;
}

/**
 * Calls the current Sandbox Verify GSTIN API.
 * POST /gst/compliance/public/gstin/verify
 *
 * @returns {{ status:number, ok:boolean, body:any }}
 */
export async function verifyGstinWithSandbox(gstin, { fetchImpl = fetch } = {}) {
  const accessToken = await getSandboxAccessToken(fetchImpl);

  let response;
  try {
    response = await withTimeout(
      fetchImpl,
      `${API_BASE}/gst/compliance/public/gstin/verify`,
      {
        method: "POST",
        headers: {
          // Sandbox JWT access token — no "Bearer " prefix
          authorization: accessToken,
          "x-api-key": sandboxConfig().apiKey,
          "x-api-version": "1.0.0",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ gstin }),
      },
    );
  } catch (err) {
    const e = new Error("Sandbox verify request failed");
    e.code = "SANDBOX_VERIFY_FAILED";
    e.cause = err;
    throw e;
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  return { status: response.status, ok: response.ok, body };
}
