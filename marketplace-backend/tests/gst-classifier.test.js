/**
 * Unit tests for GST verification classification logic.
 * Run with: node --test tests/gst-classifier.test.js
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  GSTIN_REGEX,
  DEMO_DEVELOPER_GSTIN,
  normalizeGstin,
  isValidGstinFormat,
  classifySandboxResponse,
  notVerifiedResult,
  providerUnavailableResult,
} from "../src/utils/gst-classifier.js";

// --- GSTIN format validation ---

test("normalizeGstin trims whitespace and uppercases", () => {
  assert.strictEqual(normalizeGstin("  27aabcU9603r1zm  "), "27AABCU9603R1ZM");
  assert.strictEqual(normalizeGstin(""), "");
});

test("isValidGstinFormat accepts valid GSTINs", () => {
  assert.ok(isValidGstinFormat("27AAACW7823G1ZV"));
  assert.ok(isValidGstinFormat("07AAAAA0000A1Z5")); // demo
  assert.ok(isValidGstinFormat("24ABKCS2033B1ZV")); // Sandbox example
});

test("isValidGstinFormat rejects invalid GSTINs", () => {
  assert.ok(!isValidGstinFormat(""));
  assert.ok(!isValidGstinFormat("DFEDS"));
  assert.ok(!isValidGstinFormat("AAAAAAAAAAAAAAA"));
  assert.ok(!isValidGstinFormat("27AAACW7823G1Z")); // too short
  assert.ok(!isValidGstinFormat("27AAACW7823G1ZVV")); // too long
  assert.ok(!isValidGstinFormat("27AAACW7823G0Z5")); // entity number 0 invalid ([1-9A-Z] required)
  assert.ok(isValidGstinFormat("27AAACW7823G1Z0")); // last char 0 is valid ([0-9A-Z])
  assert.ok(!isValidGstinFormat(null));
  assert.ok(!isValidGstinFormat(123));
});

// --- classifySandboxResponse ---

test("classifySandboxResponse -> NOT_VERIFIED on 404", () => {
  const res = classifySandboxResponse({ status: 404, body: null });
  assert.strictEqual(res.status, "NOT_VERIFIED");
  assert.strictEqual(res.data, null);
});

test("classifySandboxResponse -> NOT_VERIFIED on 422", () => {
  const res = classifySandboxResponse({ status: 422, body: { message: "Invalid GSTIN pattern" } });
  assert.strictEqual(res.status, "NOT_VERIFIED");
});

test("classifySandboxResponse -> NOT_VERIFIED on 400", () => {
  const res = classifySandboxResponse({ status: 400, body: {} });
  assert.strictEqual(res.status, "NOT_VERIFIED");
});

test("classifySandboxResponse -> PROVIDER_UNAVAILABLE on 429", () => {
  const res = classifySandboxResponse({ status: 429, body: {} });
  assert.strictEqual(res.status, "PROVIDER_UNAVAILABLE");
});

test("classifySandboxResponse -> PROVIDER_UNAVAILABLE on 500", () => {
  const res = classifySandboxResponse({ status: 500, body: {} });
  assert.strictEqual(res.status, "PROVIDER_UNAVAILABLE");
});

test("classifySandboxResponse -> PROVIDER_UNAVAILABLE on 502", () => {
  const res = classifySandboxResponse({ status: 502, body: {} });
  assert.strictEqual(res.status, "PROVIDER_UNAVAILABLE");
});

test("classifySandboxResponse -> VERIFIED with nested data.data (Sandbox format)", () => {
  const res = classifySandboxResponse({
    status: 200,
    body: {
      code: 200,
      data: {
        data: {
          legalName: "SANDBOX FINANCIAL TECHNOLOGIES PRIVATE LIMITED",
          bussNature: "Service Provider and Others",
          stateName: "Gujarat",
          validGstin: true,
          stateCode: "24",
          pan: "ABKCS2033B",
          gstin: "24ABKCS2033B1ZV",
          regStartDate: "06/02/2023",
          status: "Active",
        },
        status_cd: "1",
      },
      timestamp: 1775824753133,
      transaction_id: "31ac0ccf-39b6-42e0-9646-aebf47d8d980",
    },
  });

  assert.strictEqual(res.status, "VERIFIED");
  assert.ok(res.data);
  assert.strictEqual(res.data.gstin, "24ABKCS2033B1ZV");
  assert.strictEqual(res.data.legalName, "SANDBOX FINANCIAL TECHNOLOGIES PRIVATE LIMITED");
  assert.strictEqual(res.data.isDemo, false);
});

test("classifySandboxResponse -> VERIFIED with alternate field names", () => {
  const res = classifySandboxResponse({
    status: 200,
    body: {
      data: {
        legal_name: "Test Company Ltd",
        trade_name: "Test Corp",
        status: "Active",
        validGstin: true,
        gstin: "27AAACW7823G1ZV",
      },
    },
  });

  assert.strictEqual(res.status, "VERIFIED");
  assert.strictEqual(res.data.gstin, "27AAACW7823G1ZV");
  assert.strictEqual(res.data.legalName, "Test Company Ltd");
  assert.strictEqual(res.data.tradeName, "Test Corp");
});

test("classifySandboxResponse -> NOT_VERIFIED when validGstin is false", () => {
  const res = classifySandboxResponse({
    status: 200,
    body: { data: { data: { validGstin: false, status: "Active" } } },
  });
  assert.strictEqual(res.status, "NOT_VERIFIED");
});

test("classifySandboxResponse -> NOT_VERIFIED when status is cancelled", () => {
  const res = classifySandboxResponse({
    status: 200,
    body: { data: { data: { validGstin: true, status: "Cancelled" } } },
  });
  assert.strictEqual(res.status, "NOT_VERIFIED");
});

test("classifySandboxResponse -> NOT_VERIFIED when status is inactive", () => {
  const res = classifySandboxResponse({
    status: 200,
    body: { data: { data: { validGstin: true, status: "Inactive" } } },
  });
  assert.strictEqual(res.status, "NOT_VERIFIED");
});

test("classifySandboxResponse -> NOT_VERIFIED when status is suspended", () => {
  const res = classifySandboxResponse({
    status: 200,
    body: { data: { data: { validGstin: true, status: "Suspended" } } },
  });
  assert.strictEqual(res.status, "NOT_VERIFIED");
});

test("classifySandboxResponse -> PROVIDER_UNAVAILABLE on unknown status codes", () => {
  const res = classifySandboxResponse({ status: 418, body: {} }); // I'm a teapot
  assert.strictEqual(res.status, "PROVIDER_UNAVAILABLE");
});

test("classifySandboxResponse handles malformed body gracefully", () => {
  const res = classifySandboxResponse({ status: 200, body: null });
  assert.strictEqual(res.status, "NOT_VERIFIED");


  const res2 = classifySandboxResponse({ status: 200, body: "not an object" });
  assert.strictEqual(res2.status, "PROVIDER_UNAVAILABLE");

  const res3 = classifySandboxResponse({ status: 200, body: { data: "not an object" } });
  assert.strictEqual(res3.status, "PROVIDER_UNAVAILABLE");
});

// --- Demo GSTIN constant ---
test("DEMO_DEVELOPER_GSTIN is the documented value", () => {
  assert.strictEqual(DEMO_DEVELOPER_GSTIN, "07AAAAA0000A1Z5");
});