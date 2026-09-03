import { ApiError } from "../utils/api-error.js";

// In-memory rate limiting store
// Tracks attempts per IP with sliding window
const attempts = new Map();

// Configuration
const WINDOW_MS = 15 * 60 * 1000; // 15 minutes window
const MAX_ATTEMPTS = 5; // 5 attempts per window

/**
 * Rate limiter middleware for Developer Access endpoint.
 * Protects against brute-force attacks on developer keys.
 */
export const rateLimitDeveloperAccess = (req, res, next) => {
  const ip = req.ip || req.headers["x-forwarded-for"] || req.socket.remoteAddress || "unknown";
  const now = Date.now();

  // Cleanup expired entries
  for (const [key, data] of attempts.entries()) {
    if (now - data.firstAttempt > WINDOW_MS) {
      attempts.delete(key);
    }
  }

  const record = attempts.get(ip);

  if (record) {
    // Check if within window
    if (now - record.firstAttempt < WINDOW_MS) {
      if (record.count >= MAX_ATTEMPTS) {
        console.warn(`[SECURITY] Developer access rate limit exceeded for IP: ${ip}`);
        throw new ApiError(429, "Too many attempts. Please wait and try again.");
      }
      record.count += 1;
      record.lastAttempt = now;
    } else {
      // Window expired, reset
      attempts.set(ip, {
        count: 1,
        firstAttempt: now,
        lastAttempt: now,
      });
    }
  } else {
    attempts.set(ip, {
      count: 1,
      firstAttempt: now,
      lastAttempt: now,
    });
  }

  next();
};

/**
 * Reset rate limit counter for a specific IP upon successful authentication
 */
export const clearDeveloperAccessRateLimit = (req) => {
  const ip = req.ip || req.headers["x-forwarded-for"] || req.socket.remoteAddress || "unknown";
  attempts.delete(ip);
};
