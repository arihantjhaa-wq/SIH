import multer from "multer";

// Allowed image MIME types.
const ALLOWED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
]);

const MAX_IMAGE_SIZE = 5 * 1024 * 1024; // 5 MB

// Use memory storage — the file buffer will be available at req.file.buffer
// and uploaded to Cloudinary in the controller.
const storage = multer.memoryStorage();

const fileFilter = (req, file, cb) => {
  // Reject anything that isn't a supported image type.
  if (ALLOWED_TYPES.has(file.mimetype)) {
    cb(null, true);
  } else {
    const error = new Error(
      "Unsupported file type. Please upload a JPEG, PNG, WEBP, or GIF image."
    );
    error.code = "INVALID_FILE_TYPE";
    cb(error, false);
  }
};

export const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: MAX_IMAGE_SIZE },
});

export default upload;