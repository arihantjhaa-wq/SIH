import { v2 as cloudinary } from "cloudinary";
import dotenv from "dotenv";

// Ensure karein ki .env yahin load ho jaye
dotenv.config();

let _configured = false;

function ensureConfigured() {
  if (_configured) return;

  // Purana CLOUDINARY_URL delete karein taaki wo override na kare
  delete process.env.CLOUDINARY_URL;

  const cloud_name = process.env.CLOUDINARY_CLOUD_NAME?.trim();
  const api_key = process.env.CLOUDINARY_API_KEY?.trim();
  const api_secret = process.env.CLOUDINARY_API_SECRET?.trim();

  // Terminal me live check karne ke liye debug log
  console.log("👉 [Cloudinary Debug Values]:", {
    cloud_name,
    api_key,
    has_secret: Boolean(api_secret),
  });

  cloudinary.config({
    cloud_name,
    api_key,
    api_secret,
    secure: true,
  });

  _configured = true;
}

/**
 * Upload a Multer file buffer to Cloudinary.
 */
export async function uploadToCloudinary(buffer, mimetype, opts = {}) {
  ensureConfigured();
  const resourceType = mimetype?.startsWith("image/") ? "image" : "auto";
  return new Promise((resolve, reject) => {
    const stream = cloudinary.uploader.upload_stream(
      { folder: "agri-products", resource_type: resourceType, ...opts },
      (err, result) => {
        if (err) return reject(err);
        if (result) return resolve({ secure_url: result.secure_url, public_id: result.public_id });
        reject(new Error("Cloudinary upload returned no result"));
      },
    );
    stream.end(buffer);
  });
}

/**
 * Delete an image from Cloudinary by public_id.
 */
export async function deleteFromCloudinary(public_id) {
  ensureConfigured();
  return new Promise((resolve, reject) => {
    cloudinary.uploader.destroy(public_id, (err, result) => {
      if (err) return reject(err);
      resolve(result);
    });
  });
}

export default cloudinary;
