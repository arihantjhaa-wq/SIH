import http from "http";
import fs from "fs";
import dotenv from "dotenv";
dotenv.config();

const BASE = "http://localhost:7200";

function multipartPost(urlPath, fields, fileField, fileData, fileMime, fileName, token) {
  return new Promise((resolve, reject) => {
    const boundary = "----TB" + Date.now();
    const url = new URL(urlPath, BASE);
    const parts = [];
    for (const [k, v] of Object.entries(fields))
      parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`));
    if (fileData && fileName) {
      parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${fileField}"; filename="${fileName}"\r\nContent-Type: ${fileMime}\r\n\r\n`));
      parts.push(fileData);
      parts.push(Buffer.from("\r\n"));
    }
    parts.push(Buffer.from(`--${boundary}--\r\n`));
    const bodyBuf = Buffer.concat(parts);
    const headers = { "Content-Type": `multipart/form-data; boundary=${boundary}`, "Content-Length": bodyBuf.length };
    if (token) headers.Authorization = `Bearer ${token}`;
    const req = http.request({ method: "POST", hostname: url.hostname, port: url.port, path: url.pathname, headers }, res => {
      const chunks = []; res.on("data", c => chunks.push(c));
      res.on("end", () => { const raw = Buffer.concat(chunks).toString(); try { resolve({ status: res.statusCode, body: JSON.parse(raw) }); } catch { resolve({ status: res.statusCode, body: raw }); } });
    });
    req.on("error", reject); req.write(bodyBuf); req.end();
  });
}

function multipartPut(urlPath, fields, fileField, fileData, fileMime, fileName, token) {
  return new Promise((resolve, reject) => {
    const boundary = "----TB" + Date.now();
    const url = new URL(urlPath, BASE);
    const parts = [];
    for (const [k, v] of Object.entries(fields))
      parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`));
    if (fileData && fileName) {
      parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${fileField}"; filename="${fileName}"\r\nContent-Type: ${fileMime}\r\n\r\n`));
      parts.push(fileData);
      parts.push(Buffer.from("\r\n"));
    }
    parts.push(Buffer.from(`--${boundary}--\r\n`));
    const bodyBuf = Buffer.concat(parts);
    const headers = { "Content-Type": `multipart/form-data; boundary=${boundary}`, "Content-Length": bodyBuf.length };
    if (token) headers.Authorization = `Bearer ${token}`;
    const req = http.request({ method: "PUT", hostname: url.hostname, port: url.port, path: url.pathname, headers }, res => {
      const chunks = []; res.on("data", c => chunks.push(c));
      res.on("end", () => { const raw = Buffer.concat(chunks).toString(); try { resolve({ status: res.statusCode, body: JSON.parse(raw) }); } catch { resolve({ status: res.statusCode, body: raw }); } });
    });
    req.on("error", reject); req.write(bodyBuf); req.end();
  });
}

function api(method, urlPath, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlPath, BASE);
    const req = http.request({ method, hostname: url.hostname, port: url.port, path: url.pathname, headers }, res => {
      const chunks = []; res.on("data", c => chunks.push(c));
      res.on("end", () => { const raw = Buffer.concat(chunks).toString(); try { resolve({ status: res.statusCode, body: JSON.parse(raw) }); } catch { resolve({ status: res.statusCode, body: raw }); } });
    });
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

const P = (n, pass, d = "") => console.log(`${pass ? "✅" : "❌"} ${n}: ${pass ? "PASS" : "FAIL"}${d ? " — " + d : ""}`);

async function main() {
  // 1. Auth
  console.log("\n── 1. AUTH ──");
  const devKey = process.env.DEVELOPER_ACCESS_KEY;
  const auth = await api("POST", "/api/v1/auth/developer-access", JSON.stringify({ developerKey: devKey }), { "Content-Type": "application/json" });
  const token = auth.body?.data?.accessToken;
  P("Get token", !!token, auth.body?.message || `status ${auth.status}`);
  if (!token) { console.log("Aborted.\n"); return; }

  const fields = { name: "Cloud Test", category: "Grains", unit: "kg", indivPrice: "100", bizPrice: "80", minBulkQty: "10", farmer: "Tester, City" };

  // 2. Create WITH image (JPEG)
  console.log("\n── 2. CREATE WITH IMAGE ──");
  const jpegBuf = fs.readFileSync("/tmp/cloudinary-test/test.jpg");
  const cr = await multipartPost("/api/v1/products", fields, "image", jpegBuf, "image/jpeg", "test.jpg", token);
  P("Create w/ image", cr.status === 201, `status ${cr.status}: ${cr.body?.message}`);
  if (cr.status !== 201) {
    console.log("   Response:", JSON.stringify(cr.body).slice(0, 300));
  }
  let pid = cr.body?.data?._id;
  let url1 = cr.body?.data?.photo;
  if (pid) {
    P("Cloudinary URL", url1?.startsWith("https://res.cloudinary.com/"), url1?.slice(0, 80) + "...");
    P("imagePublicId", !!cr.body.data.imagePublicId, cr.body.data.imagePublicId ? "present" : "null");
    P("Fields correct", cr.body.data.name === "Cloud Test" && cr.body.data.indivPrice === 100);
  }

  // 3. Update WITHOUT image
  if (pid) {
    console.log("\n── 3. UPDATE WITHOUT IMAGE ──");
    const upd = await multipartPut(`/api/v1/products/${pid}`, { name: "Cloud Test Updated" }, null, null, null, null, token);
    P("Update", upd.status === 200, `status ${upd.status}: ${upd.body?.message}`);
    P("Name changed", upd.body?.data?.name === "Cloud Test Updated");
    P("Image unchanged", upd.body?.data?.photo === url1);
  }

  // 4. REPLACE image
  if (pid) {
    console.log("\n── 4. REPLACE IMAGE ──");
    const pngBuf = fs.readFileSync("/tmp/cloudinary-test/test.png");
    const rp = await multipartPut(`/api/v1/products/${pid}`, {}, "image", pngBuf, "image/png", "test.png", token);
    P("Replace", rp.status === 200, `status ${rp.status}: ${rp.body?.message}`);
    let url2 = rp.body?.data?.photo;
    P("New URL different", pid && url2 && url1 && url2 !== url1, url2?.slice(0, 80) + "...");
    P("New imagePublicId", !!rp.body?.data?.imagePublicId);
  }

  // 5. Validation
  console.log("\n── 5. VALIDATION ──");
  const txtBuf = Buffer.from("not an image");
  const txt = await multipartPost("/api/v1/products", fields, "image", txtBuf, "text/plain", "x.txt", token);
  P("TXT rejected", txt.status === 400, `status ${txt.status}: ${txt.body?.message}`);

  const bigBuf = Buffer.alloc(6 * 1024 * 1024, 0xff);
  const big = await multipartPost("/api/v1/products", fields, "image", bigBuf, "image/jpeg", "big.jpg", token);
  P(">5MB rejected", big.status === 413, `status ${big.status}: ${big.body?.message}`);

  // 6. Delete
  if (pid) {
    console.log("\n── 6. DELETE ──");
    const del = await api("DELETE", `/api/v1/products/${pid}`, null, { Authorization: `Bearer ${token}` });
    P("Delete", del.status === 200, del.body?.message);
  }

  // 7. No-image product
  console.log("\n── 7. CREATE WITHOUT IMAGE ──");
  const ni = await multipartPost("/api/v1/products", { ...fields, name: "NoImg" }, null, null, null, null, token);
  P("Create w/o image", ni.status === 201, `status ${ni.status}: ${ni.body?.message}`);

  console.log("\n── DONE ──");
}

main().catch(e => { console.error("FATAL:", e); process.exit(1); });
