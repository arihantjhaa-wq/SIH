/**
 * Integration tests for GST verification and developer access endpoints.
 * Requires the backend server to be running on localhost:7200.
 * Run with: node --test tests/gst-integration.test.js
 *
 * NOTE: These tests depend on a running server with MongoDB.
 */

import "dotenv/config";
import { test, describe, before, after } from "node:test";
import assert from "node:assert/strict";

const BASE_URL = "http://localhost:7200/api/v1";
const DEV_KEY = process.env.DEVELOPER_ACCESS_KEY;

/**
 * Helper to make HTTP requests to the running server.
 */
async function api(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const body = await res.json().catch(() => null);
  return { status: res.status, body };
}

describe("GST Verification Integration", () => {
  describe("FORMAT_INVALID responses", () => {
    test("empty string → FORMAT_INVALID", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({ gstin: "" }),
      });
      assert.strictEqual(body.data.status, "FORMAT_INVALID");
      assert.strictEqual(body.data.data, null);
    });

    test("too short → FORMAT_INVALID", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({ gstin: "27AAACW7823G1Z" }),
      });
      assert.strictEqual(body.data.status, "FORMAT_INVALID");
    });

    test("missing gstin field → FORMAT_INVALID", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({}),
      });
      assert.strictEqual(body.data.status, "FORMAT_INVALID");
    });

    test("null gstin → FORMAT_INVALID", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({ gstin: null }),
      });
      assert.strictEqual(body.data.status, "FORMAT_INVALID");
    });
  });

  describe("NOT_VERIFIED for real GSTINs (API verification disabled)", () => {
    test("valid GSTIN format → NOT_VERIFIED (real verification disabled)", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({ gstin: "27AAACW7823G1ZV" }),
      });
      assert.strictEqual(body.data.status, "NOT_VERIFIED");
    });

    test("lowercase → normalized → NOT_VERIFIED (real verification disabled)", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({ gstin: "27aabcu9603r1zm" }),
      });
      assert.strictEqual(body.data.status, "NOT_VERIFIED");
    });
  });

  describe("Developer Demo GSTIN", () => {
    test("unauthenticated + demo GSTIN → NOT_VERIFIED", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({ gstin: "07AAAAA0000A1Z5" }),
      });
      assert.strictEqual(body.data.status, "NOT_VERIFIED");
    });
  });

  describe("Response shape agreement", () => {
    test("all responses include statusCode, data, message, success", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({ gstin: "INVALID" }),
      });
      assert.ok("statusCode" in body);
      assert.ok("data" in body);
      assert.ok("message" in body);
      assert.ok("success" in body);
    });

    test("FORMAT_INVALID includes status and message in data", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        body: JSON.stringify({ gstin: "INVALID" }),
      });
      assert.ok("status" in body.data);
      assert.ok("message" in body.data);
    });
  });
});

describe("Developer Access Integration", () => {
  let developerToken = null;

  test("valid key returns tokens and isDeveloper", async () => {
    assert.ok(DEV_KEY, "DEVELOPER_ACCESS_KEY must be set in environment");
    const { body } = await api("/auth/developer-access", {
      method: "POST",
      body: JSON.stringify({ developerKey: DEV_KEY }),
    });
    assert.strictEqual(body.statusCode, 200);
    assert.ok(body.data.accessToken);
    assert.ok(body.data.user.isDeveloper);
    assert.strictEqual(body.data.user.username, "__developer__");
    developerToken = body.data.accessToken;
  });

  test("invalid key returns 401", async () => {
    const { status, body } = await api("/auth/developer-access", {
      method: "POST",
      body: JSON.stringify({ developerKey: "wrong_key_that_is_long_enough_12345678901234567890" }),
    });
    assert.ok(status === 401 || body.statusCode === 401);
  });

  test("missing key returns 400", async () => {
    const { status, body } = await api("/auth/developer-access", {
      method: "POST",
      body: JSON.stringify({}),
    });
    assert.ok(status === 400 || body.statusCode === 400);
  });

  test("/me returns isDeveloper for authenticated developer", async () => {
    const { body } = await api("/auth/me", {
      headers: { Authorization: `Bearer ${developerToken}` },
    });
    assert.strictEqual(body.statusCode, 200);
    assert.ok(body.data.user.isDeveloper);
    assert.strictEqual(body.data.user.username, "__developer__");
  });

  describe("Developer Demo GSTIN with developer token", () => {
    test("authenticated developer + demo GSTIN → VERIFIED with isDemo", async () => {
      const { body } = await api("/gst/verify", {
        method: "POST",
        headers: { Authorization: `Bearer ${developerToken}` },
        body: JSON.stringify({ gstin: "07AAAAA0000A1Z5" }),
      });
      assert.strictEqual(body.data.status, "VERIFIED");
      assert.ok(body.data.data.isDemo);
      assert.strictEqual(body.data.data.gstin, "07AAAAA0000A1Z5");
      assert.ok(body.data.data.legalName.includes("AgriDirect"));
    });
  });
});

describe("Security Checks", () => {
  test("developer access endpoint does not leak secret in response", async () => {
    const { body } = await api("/auth/developer-access", {
      method: "POST",
      body: JSON.stringify({ developerKey: DEV_KEY }),
    });
    const responseStr = JSON.stringify(body);
    assert.ok(!responseStr.includes(DEV_KEY?.slice(0, 12) || ""), "Response must not contain the developer key");
  });

  test("healthcheck returns healthy", async () => {
    const { body } = await api("/healthcheck");
    assert.strictEqual(body.statusCode, 200);
    assert.ok(body.success);
  });
});