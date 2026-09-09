/**
 * Unit tests for GST verification classification helpers (simplified).
 * Run with: node --test tests/gst-classifier.test.js
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  GSTIN_REGEX,
  DEMO_DEVELOPER_GSTIN,
  normalizeGstin,
  isValidGstinFormat,
  notVerifiedResult,
  verificationDisabledResult,
  formatInvalidResult,
  VERIFICATION_DISABLED_MSG,
} from "../src/utils/gst-classifier.js";

// --- GSTIN format validation ---

test("normalizeGstin trims whitespace and uppercases", () => {
  assert.strictEqual(normalizeGstin("  27aabcU9603r1zm  "), "27AABCU9603R1ZM");
  assert.strictEqual(normalizeGstin(""), "");
});

test("isValidGstinFormat accepts valid GSTINs", () => {
  assert.ok(isValidGstinFormat("27AAACW7823G1ZV"));
  assert.ok(isValidGstinFormat("07AAAAA0000A1Z5")); // demo
  assert.ok(isValidGstinFormat("24ABKCS2033B1ZV"));
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

// --- Demo GSTIN constant ---

test("DEMO_DEVELOPER_GSTIN is the documented value", () => {
  assert.strictEqual(DEMO_DEVELOPER_GSTIN, "07AAAAA0000A1Z5");
});

// --- Result helpers ---

test("notVerifiedResult returns correct shape", () => {
  const result = notVerifiedResult();
  assert.strictEqual(result.status, "NOT_VERIFIED");
  assert.strictEqual(result.data, null);
  assert.ok(typeof result.message === "string");
});

test("verificationDisabledResult returns correct shape", () => {
  const result = verificationDisabledResult();
  assert.strictEqual(result.status, "VERIFICATION_DISABLED");
  assert.strictEqual(result.data, null);
  assert.strictEqual(result.message, VERIFICATION_DISABLED_MSG);
});

test("formatInvalidResult returns correct shape", () => {
  const result = formatInvalidResult("Test error message");
  assert.strictEqual(result.status, "FORMAT_INVALID");
  assert.strictEqual(result.data, null);
  assert.strictEqual(result.message, "Test error message");
});