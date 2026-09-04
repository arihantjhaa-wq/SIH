// Test developer access flow without exposing secrets in command line
import { readFileSync } from "fs";

// Load .env manually (no dotenv, no external deps)
const envContent = readFileSync(".env", "utf8");
const env = {};
for (const line of envContent.split("\n")) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) continue;
  const eq = trimmed.indexOf("=");
  if (eq === -1) continue;
  const key = trimmed.slice(0, eq).trim();
  const value = trimmed.slice(eq + 1).trim();
  env[key] = value;
}

const DEV_KEY = env.DEVELOPER_ACCESS_KEY;
const BASE_URL = "http://localhost:7200/api/v1";

if (!DEV_KEY) {
  console.error("ERROR: DEVELOPER_ACCESS_KEY not set");
  process.exit(1);
}

console.log("=== Developer Access Test ===");
console.log("DEV_KEY length:", DEV_KEY.length, "chars (expected 32+)");
console.log("Backend env check:");
console.log("  DEVELOPER_ACCESS_ENABLED:", env.DEVELOPER_ACCESS_ENABLED);
console.log("  DEVELOPER_ACCESS_KEY exists:", Boolean(DEV_KEY));
console.log("  Key length >= 32:", DEV_KEY.length >= 32);
console.log("");

// Step 1: Test with wrong key
console.log("--- Step 1: Wrong key test ---");
const wrongRes = await fetch(`${BASE_URL}/auth/developer-access`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ developerKey: "wrong_key_xxxxxxxxxxxxxxxxxxxxxxxxxxx" }),
});
const wrongBody = await wrongRes.json();
console.log("Status:", wrongRes.status);
console.log("Response message:", wrongBody.message);
console.log("");

// Step 2: Test with empty key
console.log("--- Step 2: Empty key test ---");
const emptyRes = await fetch(`${BASE_URL}/auth/developer-access`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({}),
});
const emptyBody = await emptyRes.json();
console.log("Status:", emptyRes.status);
console.log("Response message:", emptyBody.message);
console.log("");

// Step 3: Test with correct key
console.log("--- Step 3: Correct key test ---");
const correctRes = await fetch(`${BASE_URL}/auth/developer-access`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ developerKey: DEV_KEY }),
});
const correctBody = await correctRes.json();
console.log("Status:", correctRes.status);
console.log("Success:", correctBody.success);
console.log("User present:", Boolean(correctBody.data?.user));
console.log("User username:", correctBody.data?.user?.username);
console.log("User isDeveloper:", correctBody.data?.user?.isDeveloper);
console.log("AccessToken present:", Boolean(correctBody.data?.accessToken));
console.log("AccessToken length:", correctBody.data?.accessToken?.length);
console.log("");

if (correctRes.status !== 200 || !correctBody.data?.accessToken) {
  console.error("FAIL: Developer Access did not return a valid session");
  console.error("Full response (safe):", JSON.stringify(correctBody, (k, v) => {
    if (k === "accessToken" || k === "refreshToken") return v ? "***" : v;
    return v;
  }, 2));
  process.exit(1);
}

const accessToken = correctBody.data.accessToken;
const user = correctBody.data.user;

console.log("✓ Developer Access successful");
console.log("");

// Step 4: Test /auth/me with the token
console.log("--- Step 4: /auth/me test ---");
const meRes = await fetch(`${BASE_URL}/auth/me`, {
  headers: { Authorization: `Bearer ${accessToken}` },
});
const meBody = await meRes.json();
console.log("Status:", meRes.status);
console.log("User username:", meBody.data?.user?.username);
console.log("User isDeveloper:", meBody.data?.user?.isDeveloper);
console.log("User email:", meBody.data?.user?.email);
console.log("");

if (!meBody.data?.user?.isDeveloper) {
  console.error("FAIL: /auth/me did not recognize developer");
  process.exit(1);
}

console.log("✓ /auth/me recognizes developer");
console.log("");

// Step 5: Test GST verification with demo GSTIN
console.log("--- Step 5: GST developer demo test ---");
const demoRes = await fetch(`${BASE_URL}/gst/verify`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  },
  body: JSON.stringify({ gstin: "07AAAAA0000A1Z5" }),
});
const demoBody = await demoRes.json();
console.log("Status:", demoRes.status);
console.log("GST status:", demoBody.data?.status);
console.log("Is demo:", demoBody.data?.data?.isDemo);
console.log("Legal name:", demoBody.data?.data?.legalName);
console.log("");

if (demoBody.data?.status !== "VERIFIED" || !demoBody.data?.data?.isDemo) {
  console.error("FAIL: Developer demo GSTIN did not verify");
  process.exit(1);
}

console.log("✓ Developer Demo GSTIN verified");
console.log("");

// Step 6: Test malformed GSTIN
console.log("--- Step 6: Malformed GSTIN test ---");
const malformedRes = await fetch(`${BASE_URL}/gst/verify`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  },
  body: JSON.stringify({ gstin: "INVALID" }),
});
const malformedBody = await malformedRes.json();
console.log("Status:", malformedRes.status);
console.log("GST status:", malformedBody.data?.status);
console.log("");

if (malformedBody.data?.status !== "FORMAT_INVALID") {
  console.error("FAIL: Malformed GSTIN should return FORMAT_INVALID");
  process.exit(1);
}

console.log("✓ Malformed GSTIN returns FORMAT_INVALID");
console.log("");

// Step 7: Test unauthenticated demo GSTIN attempt
console.log("--- Step 7: Unauthenticated demo GSTIN test ---");
const noAuthRes = await fetch(`${BASE_URL}/gst/verify`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ gstin: "07AAAAA0000A1Z5" }),
});
const noAuthBody = await noAuthRes.json();
console.log("Status:", noAuthRes.status);
console.log("GST status (no auth):", noAuthBody.data?.status);
console.log("");

if (noAuthBody.data?.status === "VERIFIED") {
  console.error("FAIL: Unauthenticated user got VERIFIED for demo GSTIN");
  process.exit(1);
}

console.log("✓ Unauthenticated user cannot use demo GSTIN");
console.log("");

console.log("═══════════════════════════════════════");
console.log("  ALL TESTS PASSED");
console.log("═══════════════════════════════════════");
