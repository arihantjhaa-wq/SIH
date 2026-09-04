/**
 * Unit tests for sandbox-client.js with mocked fetch.
 * Run with: node --test tests/sandbox-client.test.js
 */

import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
  sandboxConfig,
  hasSandboxCredentials,
  getSandboxAccessToken,
  verifyGstinWithSandbox,
  clearSandboxTokenCache,
} from "../src/utils/sandbox-client.js";

describe("sandbox-client", () => {
  beforeEach(() => {
    clearSandboxTokenCache();
    delete process.env.SANDBOX_API_KEY;
    delete process.env.SANDBOX_API_SECRET;
    delete process.env.SANDBOX_AUTH_TOKEN;
  });

  describe("sandboxConfig", () => {
    test("returns undefined when env vars missing", () => {
      const config = sandboxConfig();
      assert.strictEqual(config.apiKey, undefined);
      assert.strictEqual(config.apiSecret, undefined);
    });

    test("returns apiSecret from SANDBOX_AUTH_TOKEN fallback", () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_AUTH_TOKEN = "secret_live_xyz";
      const config = sandboxConfig();
      assert.strictEqual(config.apiKey, "key_live_abc");
      assert.strictEqual(config.apiSecret, "secret_live_xyz");
    });

    test("prefers SANDBOX_API_SECRET over SANDBOX_AUTH_TOKEN", () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_API_SECRET = "actual_secret";
      process.env.SANDBOX_AUTH_TOKEN = "fallback_token";
      const config = sandboxConfig();
      assert.strictEqual(config.apiSecret, "actual_secret");
    });
  });

  describe("hasSandboxCredentials", () => {
    test("returns false when credentials missing", () => {
      assert.strictEqual(hasSandboxCredentials(), false);
    });

    test("returns true when both key and secret present", () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_AUTH_TOKEN = "secret_live_xyz";
      assert.strictEqual(hasSandboxCredentials(), true);
    });
  });

  describe("getSandboxAccessToken", () => {
    test("throws SANDBOX_CONFIG_ERROR when credentials missing", async () => {
      await assert.rejects(
        () => getSandboxAccessToken(),
        { code: "SANDBOX_CONFIG_ERROR" }
      );
    });

    test("caches token and returns on second call", async () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_AUTH_TOKEN = "secret_live_xyz";

      let callCount = 0;
      const mockFetch = async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          data: { access_token: "cached_token_123" },
        }),
      });

      const token1 = await getSandboxAccessToken(mockFetch);
      const token2 = await getSandboxAccessToken(mockFetch);

      assert.strictEqual(token1, "cached_token_123");
      assert.strictEqual(token2, "cached_token_123");
      // Only 1 fetch call made (second uses cache)
    });

    test("throws SANDBOX_AUTH_FAILED on non-ok response", async () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_AUTH_TOKEN = "secret_live_xyz";

      const mockFetch = async () => ({
        ok: false,
        status: 401,
        json: async () => ({ error: "Unauthorized" }),
      });

      await assert.rejects(
        () => getSandboxAccessToken(mockFetch),
        { code: "SANDBOX_AUTH_FAILED" }
      );
    });

    test("throws SANDBOX_AUTH_FAILED when access_token missing from response", async () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_AUTH_TOKEN = "secret_live_xyz";

      const mockFetch = async () => ({
        ok: true,
        status: 200,
        json: async () => ({ data: {} }),
      });

      await assert.rejects(
        () => getSandboxAccessToken(mockFetch),
        { code: "SANDBOX_AUTH_FAILED" }
      );
    });
  });

  describe("verifyGstinWithSandbox", () => {
    test("calls verify API with correct headers", async () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_AUTH_TOKEN = "secret_live_xyz";

      let capturedUrl, capturedOptions;
      const mockFetch = async (url, options) => {
        if (url.endsWith("/authenticate")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ data: { access_token: "cached_token_123" } }),
          };
        }
        capturedUrl = url;
        capturedOptions = options;
        return {
          ok: true,
          status: 200,
          json: async () => ({
            code: 200,
            data: {
              data: { gstin: "24ABKCS2033B1ZV", validGstin: true, status: "Active" },
            },
          }),
        };
      };

      const result = await verifyGstinWithSandbox("24ABKCS2033B1ZV", { fetchImpl: mockFetch });

      assert.strictEqual(capturedUrl, "https://api.sandbox.co.in/gst/compliance/public/gstin/verify");
      assert.strictEqual(capturedOptions.method, "POST");
      assert.strictEqual(capturedOptions.headers["x-api-key"], "key_live_abc");
      assert.strictEqual(capturedOptions.headers["x-api-version"], "1.0.0");
      assert.strictEqual(capturedOptions.headers["authorization"], "cached_token_123");
      // Verify no "Bearer " prefix
      assert.ok(!capturedOptions.headers.authorization.startsWith("Bearer"));
      assert.strictEqual(JSON.parse(capturedOptions.body).gstin, "24ABKCS2033B1ZV");
      assert.strictEqual(result.status, 200);
      assert.strictEqual(result.body.data.data.validGstin, true);
    });

    test("returns status and body on failure", async () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_AUTH_TOKEN = "secret_live_xyz";

      const mockFetch = async (url) => {
        if (url.endsWith("/authenticate")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ data: { access_token: "token_123" } }),
          };
        }
        return {
          ok: false,
          status: 422,
          json: async () => ({ message: "Invalid GSTIN pattern" }),
        };
      };

      const result = await verifyGstinWithSandbox("INVALID", { fetchImpl: mockFetch });

      assert.strictEqual(result.status, 422);
      assert.strictEqual(result.ok, false);
      assert.deepStrictEqual(result.body, { message: "Invalid GSTIN pattern" });
    });

    test("throws SANDBOX_VERIFY_FAILED on network error", async () => {
      process.env.SANDBOX_API_KEY = "key_live_abc";
      process.env.SANDBOX_AUTH_TOKEN = "secret_live_xyz";

      let callCount = 0;
      const mockFetch = async (url) => {
        callCount++;
        if (url.endsWith("/authenticate")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ data: { access_token: "token_123" } }),
          };
        }
        throw new Error("Network error");
      };

      await assert.rejects(
        () => verifyGstinWithSandbox("24ABKCS2033B1ZV", { fetchImpl: mockFetch }),
        { code: "SANDBOX_VERIFY_FAILED" }
      );
    });
  });
});
