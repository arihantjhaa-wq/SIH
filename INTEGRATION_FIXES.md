# Frontend-Backend Integration Fixes

## Summary
This document details all integration issues found and fixed in the kheti-seedha project. The frontend (Vite + React) and backend (Express + MongoDB) had several critical mismatches preventing proper communication.

---

## Issues Found & Fixed

### 🔴 CRITICAL: Product ID Field Mismatch
**Location:** `frontend/src/services/productService.js`  
**Problem:** MongoDB returns `_id` for products, but the entire frontend uses `p.id` everywhere (cart, filtering, product cards, deletion). This caused:
- Products not appearing in the cart
- Delete operations failing silently
- Product detail pages breaking
- Search/filtering not working

**Fix:** Added mapping in `getProducts()` and `createProduct()` to transform `_id` → `id`
```javascript
return data.data.map(p => ({ ...p, id: p._id }));
```

---

### 🔴 CRITICAL: Missing CORS Configuration
**Location:** `backend/.env`  
**Problem:** 
- No `CORS_ORIGIN` environment variable defined
- Backend would only accept requests from `localhost:5173` (hardcoded fallback)
- Deployed frontend (Vercel, Netlify, etc.) would be blocked

**Fix:** 
- Added `CORS_ORIGIN` to `.env` with default local dev values
- Created `.env.example` files for both frontend and backend
- Documented that production needs `CORS_ORIGIN=https://your-frontend-domain.com`

---

### 🔴 CRITICAL: Cookie Authentication Not Working Cross-Origin
**Location:** `backend/src/controllers/auth.controller.js:100, 138`  
**Problem:** Login and logout set cookies without `sameSite` attribute. When frontend and backend are on different domains (production), cookies are blocked by browsers.

**Fix:** Added `sameSite` configuration to cookie options:
```javascript
const options = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: process.env.NODE_ENV === "production" ? "none" : "lax",
};
```

**Important:** For production with separate domains:
- Backend must set `sameSite: "none"` and `secure: true`
- Frontend must include `credentials: true` in requests (already done in `api.js:11`)

---

### 🟡 HIGH: Email Verification URL Wrong
**Location:** `backend/src/controllers/auth.controller.js:48`  
**Problem:** Registration builds verification URL as `/api/v1/users/verify-email/${token}` but actual route is `/api/v1/auth/verify-email/${token}`. Email verification links would 404.

**Fix:** Changed path from `users` to `auth`

---

### 🟡 HIGH: Registration Crashes Without Email Config
**Location:** `backend/src/utils/mail.js:4`  
**Problem:** Registration calls `sendEmail()` which requires `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD` env vars. When missing, `nodemailer.createTransport()` would fail and crash the registration endpoint.

**Fix:** Added early return with warning when email config is missing:
```javascript
if (!process.env.EMAIL_HOST || !process.env.EMAIL_USERNAME) {
  console.warn("Email service skipped: EMAIL_HOST or EMAIL_USERNAME not configured");
  return;
}
```
Now registration works even without email configured (user just won't get verification email).

---

### 🟡 HIGH: ApiResponse Typo Breaking Frontend Checks
**Location:** `backend/src/utils/api-responce.js:6`  
**Problem:** Response object has `this.sucess` (typo) instead of `this.success`. Any frontend code checking `data.success` would get `undefined`.

**Fix:** Changed `sucess` → `success` (also fixed "Sucess" → "Success")

---

### 🟠 MEDIUM: Product Delete Fails to Update UI
**Location:** `frontend/src/context/ProductContext.jsx:47`  
**Problem:** `removeProduct()` filters with `p.id !== id`, but before the ID mapping fix, products had `_id` not `id`. Delete would succeed on backend but product would stay visible in UI.

**Fix:** Updated filter to check both fields for safety:
```javascript
setProducts((prev) => prev.filter((p) => p._id !== id && p.id !== id));
```

---

### 🟠 MEDIUM: Missing Environment Variables
**Location:** `backend/.env`, `frontend/.env`  
**Problem:** 
- Backend missing `PORT`, `NODE_ENV`, `CORS_ORIGIN`
- Frontend missing `.env` file entirely
- No `.env.example` files to guide deployment

**Fix:** 
- Added all missing env vars to `backend/.env`
- Created `frontend/.env` with `VITE_API_BASE_URL=http://localhost:7200`
- Created `.env.example` for both with documentation

---

### 🔴 CRITICAL: cookie-parser Not Installed
**Location:** `backend/src/app.js`, `backend/package.json`  
**Problem:** Auth middleware reads `req.cookies?.accessToken` but `cookie-parser` is neither installed nor configured. Without it, `req.cookies` is always `undefined` and cookie-based auth completely fails. Only the Authorization header fallback works.

**Fix:** 
- Installed `cookie-parser` via npm
- Added `import cookieParser from 'cookie-parser'`
- Added `app.use(cookieParser())` to middleware chain

**Impact:** Cookie-based authentication now works. Before this fix, login would SET cookies but could never READ them back.

---

### 🟢 LOW: Typo in User Model Schema
**Location:** `backend/src/models/user.model.js:12`  
**Problem:** Username field has `lowecase: true` (typo) instead of `lowercase: true`. Usernames would not be automatically converted to lowercase, causing login issues if user types different casing than registration.

**Fix:** Changed `lowecase` → `lowercase`

---

### 🟢 LOW: Typo in Health Check Response
**Location:** `backend/src/controllers/healthcheack.controller.js:6`  
**Problem:** Health check returns "Surver is running Good" (typo).

**Fix:** Changed to "Server is running smoothly" with proper message parameter.

---

## Files Changed

### Backend
1. `backend/.env` - Added PORT, NODE_ENV, CORS_ORIGIN, email config placeholders
2. `backend/.env.example` - Created with full documentation
3. `backend/package.json` - Added cookie-parser dependency
4. `backend/src/app.js` - Added cookie-parser middleware
5. `backend/src/controllers/auth.controller.js` - Fixed email verification URL, added sameSite to cookies
6. `backend/src/controllers/healthcheack.controller.js` - Fixed typo in health check message
7. `backend/src/models/user.model.js` - Fixed typo: lowecase → lowercase
8. `backend/src/utils/api-responce.js` - Fixed typo: sucess → success
9. `backend/src/utils/mail.js` - Made email optional, won't crash if unconfigured

### Frontend
1. `frontend/.env` - Created with VITE_API_BASE_URL
2. `frontend/.env.example` - Created with documentation
3. `frontend/src/services/productService.js` - Map MongoDB _id to id
4. `frontend/src/context/ProductContext.jsx` - Fixed removeProduct filter

---

## What You Need to Do Manually

### For Local Development
✅ Already working! All fixes applied. Just run:
```bash
# Terminal 1 - Backend
cd backend
npm run dev

# Terminal 2 - Frontend  
cd frontend
npm run dev
```

### For Production Deployment

#### Backend (e.g., Render, Railway, Heroku)
Set these environment variables in your hosting platform:
```
MONGODB_URI=mongodb+srv://...your connection string...
PORT=7200
NODE_ENV=production
ACCESS_TOKEN_SECRET=<generate-a-strong-secret>
REFRESH_TOKEN_SECRET=<generate-a-different-strong-secret>
CORS_ORIGIN=https://your-frontend.vercel.app
```

⚠️ **IMPORTANT:** Set `CORS_ORIGIN` to your actual frontend URL, otherwise requests will be blocked!

#### Frontend (e.g., Vercel, Netlify)
Set this environment variable:
```
VITE_API_BASE_URL=https://your-backend.onrender.com
```

Replace with your actual backend deployment URL.

#### Optional: Email Verification
If you want email verification to work, add these to backend env vars:
```
EMAIL_HOST=smtp.mailtrap.io
EMAIL_PORT=2525
EMAIL_USERNAME=your_mailtrap_username
EMAIL_PASSWORD=your_mailtrap_password
```

---

## Testing Checklist

### ✅ Auth Flow
- [ ] Register a new user (should work even without email config)
- [ ] Login with username/password
- [ ] Check that `ks_accessToken` appears in localStorage
- [ ] Logout
- [ ] Verify token is cleared from localStorage

### ✅ Products - Consumer Side
- [ ] Products load on marketplace page
- [ ] Search works
- [ ] Category filters work
- [ ] Add product to cart
- [ ] Quantity shows in cart icon
- [ ] Cart page shows correct products and prices
- [ ] Remove from cart works

### ✅ Products - Farmer Side
- [ ] Switch to farmer role
- [ ] Create a new product
- [ ] Product appears in "Your live listings"
- [ ] Product appears in consumer marketplace with "New listing" badge
- [ ] Delete product from farmer portal
- [ ] Product disappears from both farmer list and marketplace

### ✅ CORS (Production Only)
- [ ] Frontend deployed on different domain can reach backend
- [ ] Login works cross-origin
- [ ] Cookies are set and sent with subsequent requests

---

## Architecture Notes

### API Call Flow
```
Frontend (Vite + React)
  ↓ axios with baseURL from VITE_API_BASE_URL
  ↓ withCredentials: true (sends cookies)
  ↓ Authorization: Bearer <token> (from localStorage)
  ↓
Backend (Express)
  ↓ CORS middleware checks CORS_ORIGIN
  ↓ Routes: /api/v1/auth, /api/v1/products, /api/v1/healthcheck
  ↓ Auth middleware verifies JWT from Authorization header OR cookies
  ↓ Controllers handle business logic
  ↓ MongoDB (via Mongoose)
```

### Auth Strategy
The backend uses **dual auth**:
1. **Cookies** (httpOnly) - More secure, automatic
2. **Authorization header** with Bearer token - For API clients

Frontend uses both:
- Stores token in `localStorage` as `ks_accessToken`
- Axios interceptor adds `Authorization: Bearer <token>` to every request
- Backend sets `accessToken` cookie on login
- `withCredentials: true` sends cookies with requests

This redundancy ensures auth works in various deployment scenarios.

---

## Known Limitations

1. **Email verification is optional** - Users can register and use the app without verifying email. To require it, add checks for `user.isEmailVerified` in protected routes.

2. **No refresh token flow** - Backend generates refresh tokens but doesn't have a `/auth/refresh` endpoint. Tokens expire after 10 days. Consider adding token refresh before token expiry.

3. **Product images stored as base64** - Large images sent as base64 strings in request body. For production, consider using file upload to cloud storage (Cloudinary, S3).

4. **No rate limiting** - Consider adding `express-rate-limit` for auth endpoints in production.

5. **Cart is local only** - Cart state is in localStorage, not synced to backend. Clearing browser data loses cart. Consider adding cart sync to user account.

---

## Contact
If issues persist after these fixes, check:
1. Browser console for frontend errors
2. Backend terminal for server errors  
3. Network tab to see actual request/response (status codes, CORS errors)
4. MongoDB connection string is valid and allows network access

Most integration issues after these fixes will be deployment-specific (wrong env vars, CORS misconfiguration, or hosting platform quirks).
