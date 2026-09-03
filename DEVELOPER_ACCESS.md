# Developer Access

## Overview

Developer Access is a secure authentication feature that allows developers to quickly authenticate with a server-side secret key instead of repeatedly going through normal Login/Register flows during development and demos. This is a **development convenience feature only** and must be properly secured.

## ⚠️ Security Warning

**IMPORTANT**: Developer Access should be **DISABLED in production environments**. This feature is intended only for:
- Local development
- Demo environments
- Testing/staging environments with restricted network access

## Setup Instructions

### 1. Generate a Strong Developer Key

Generate a cryptographically random key with at least 32 characters:

```bash
node -e "console.log('AGRI_DEV_' + require('crypto').randomBytes(32).toString('hex'))"
```

Example output (DO NOT use this exact key):
```
AGRI_DEV_<your_random_64_hex_characters>
```

### 2. Configure the Backend

Edit `marketplace-backend/.env` and add:

```env
# Developer Access Configuration (development/demo only)
DEVELOPER_ACCESS_ENABLED=true
DEVELOPER_ACCESS_KEY=<your-generated-key-here>
```

**Important**: 
- Never commit the real key to version control
- The `.env` file is already in `.gitignore`
- The `.env.example` file contains safe placeholder values only

### 3. Start the Application

Start the backend:
```bash
cd marketplace-backend
npm run dev
```

Start the frontend:
```bash
cd frontend
npm run dev
```

### 4. Using Developer Access

1. Open the application in your browser: `http://localhost:5173`
2. On the login page, click the subtle "Developer Access" link (shown in gray text)
3. Enter your developer key from the `.env` file
4. Click "Enter Developer Mode"
5. You will be authenticated as a developer user

After authentication:
- You can select "Farmer" or "Consumer" role like any normal user
- You can access all protected routes
- You can logout normally
- Your session persists across page refreshes (like normal login)

## How It Works

### Backend (marketplace-backend)

1. **Endpoint**: `POST /api/v1/auth/developer-access`
   - Request body: `{ "developerKey": "<your-key>" }`
   - Response: Same structure as normal login (JWT tokens + user object)

2. **Security Measures**:
   - Server-side key verification only (never exposed to frontend)
   - Constant-time comparison prevents timing attacks (`crypto.timingSafeEqual`)
   - Rate limiting: 5 attempts per 15-minute window per IP
   - Secure logging (keys never logged, only attempt timestamps)
   - Startup validation (fails if key is missing or too short when enabled)

3. **Authentication Flow**:
   - Validates the key against `DEVELOPER_ACCESS_KEY` environment variable
   - Creates or retrieves a special `__developer__` user in the database
   - Generates standard JWT access and refresh tokens
   - Returns authenticated session identical to normal login

### Frontend (frontend)

1. **New Page**: `src/pages/DeveloperAccess.jsx`
   - Matches existing design system (dark theme, gold accents)
   - Password input field (hides the key)
   - Error handling and loading states

2. **Updated Files**:
   - `src/services/authService.js` - Added `developerAccessLogin()` function
   - `src/context/AuthContext.jsx` - Added `developerLogin()` hook
   - `src/pages/Login.jsx` - Added "Developer Access" link
   - `src/App.jsx` - Added routing for developer view

3. **Token Storage**: Uses the same `localStorage` mechanism as normal login (`ks_accessToken`)

## Security Features

### ✅ What's Protected

- Developer key stored server-side only (never in frontend code or bundle)
- Constant-time comparison prevents timing attacks
- Rate limiting prevents brute-force attempts (5 attempts per 15 minutes)
- Key never appears in:
  - API responses
  - Logs
  - URLs
  - Git history
  - Frontend source code or bundles
- Client cannot bypass authentication by sending fake roles or tokens
- Protected routes require valid JWT (same as normal users)

### ✅ What's Validated

- Startup validation ensures key is configured and strong (≥32 characters)
- Request validation ensures key is present, non-empty, and correct type
- Environment check ensures developer access can be disabled for production

### ⚠️ Known Limitations (Prototype)

1. **In-memory rate limiting**: Rate limiter resets on server restart. For production-grade systems, use Redis or a persistent store.

2. **Single developer user**: All developers share the `__developer__` user account. For proper dev environments, consider implementing unique developer identities.

3. **No account lockout**: After the rate limit window expires (15 minutes), attempts can resume. Production systems should consider progressive backoff.

4. **No audit trail**: Developer access events are logged to console only. Production systems should log to a dedicated audit log with retention.

5. **No user role field**: The current User model has no `role` field. The `isDeveloper` flag is only returned in the API response for frontend UI purposes. If you later add proper role-based authorization at the database level, refactor accordingly.

## Disabling Developer Access

### For Production

Set in `marketplace-backend/.env`:

```env
DEVELOPER_ACCESS_ENABLED=false
```

When disabled:
- The endpoint returns `403 Developer access is currently unavailable`
- No key validation occurs
- No rate limiting overhead

### For Testing Disabled State

Temporarily set `DEVELOPER_ACCESS_ENABLED=false` in `.env` and restart the backend. The developer access endpoint should return a 403 error.

## Rotating the Developer Key

To change the developer key:

1. Generate a new random key:
   ```bash
   node -e "console.log('AGRI_DEV_' + require('crypto').randomBytes(32).toString('hex'))"
   ```

2. Update `marketplace-backend/.env`:
   ```env
   DEVELOPER_ACCESS_KEY=<new-key>
   ```

3. Restart the backend server:
   ```bash
   cd marketplace-backend
   npm run dev
   ```

4. Share the new key securely with your team (never via email or public channels)

## Troubleshooting

### "Please enter your developer key"
- Ensure you entered a non-empty key in the frontend
- Check that the key doesn't have leading/trailing whitespace

### "Invalid developer key"
- Verify you copied the correct key from `.env`
- Ensure the backend is using the same `.env` file
- Check that `DEVELOPER_ACCESS_KEY` in `.env` matches what you entered

### "Developer access is currently unavailable"
- Check that `DEVELOPER_ACCESS_ENABLED=true` in `marketplace-backend/.env`
- Restart the backend after changing the configuration

### "Too many attempts. Please wait and try again."
- You've exceeded 5 failed attempts in a 15-minute window
- Wait 15 minutes and try again with the correct key
- Restart the backend server to reset the rate limiter (development only)

### "FATAL: DEVELOPER_ACCESS_KEY must be at least 32 characters"
- Your key is too short (security requirement)
- Generate a new strong key using the command in Setup Instructions

### Normal login/register not working
- Developer Access does not interfere with normal authentication
- Verify your database connection is working
- Check backend logs for specific error messages

## Testing Checklist

Before deploying or sharing your environment, verify:

- [ ] `.env` is in `.gitignore` and not tracked by git
- [ ] Real developer key is NOT in any tracked files
- [ ] `.env.example` has only placeholder values
- [ ] `git status` shows no tracked `.env` files
- [ ] `git diff` shows no secrets
- [ ] Frontend bundle contains no secrets (run `npm run build` and inspect `dist/`)
- [ ] Developer access works with valid key
- [ ] Developer access rejects wrong key
- [ ] Rate limiting triggers after 5 failed attempts
- [ ] Normal login/register still work
- [ ] Developer can access protected routes after authentication
- [ ] Developer logout works
- [ ] Developer access returns 403 when `DEVELOPER_ACCESS_ENABLED=false`

## Architecture Notes

### Why a Special `__developer__` User?

The implementation creates a dedicated database user with username `__developer__` rather than bypassing authentication entirely. This approach:

- Reuses existing JWT authentication infrastructure
- Works seamlessly with existing auth middleware
- Maintains consistent session behavior
- Allows developer access to be tracked in logs
- Prevents collision with real usernames (double underscore prefix)

### Why Not Store in Frontend?

Storing the developer key in frontend code or environment variables would:
- Expose it in the built JavaScript bundle
- Allow anyone inspecting the frontend to extract it
- Defeat the security purpose entirely

The server-side-only approach ensures the key remains secret.

### Normal Login/Register Compatibility

Developer Access is completely separate from normal authentication:
- Different endpoint (`/api/v1/auth/developer-access` vs `/api/v1/auth/login`)
- Different request body (`developerKey` vs `username`/`password`)
- Different UI route (subtle link vs prominent buttons)
- Same JWT token format (compatible with all protected routes)

Normal users never see or interact with developer access unless they specifically click the gray "Developer Access" link on the login page.

## Production Deployment Checklist

Before deploying to production:

- [ ] Set `DEVELOPER_ACCESS_ENABLED=false` in production `.env`
- [ ] Remove or invalidate development/staging developer keys
- [ ] Verify the disabled state returns 403
- [ ] Ensure production firewall/security groups restrict access
- [ ] Review and rotate all other secrets (JWT secrets, database passwords, etc.)
- [ ] Set `NODE_ENV=production` for secure cookies
- [ ] Enable HTTPS for production deployment
- [ ] Configure proper CORS origins for production frontend URL

## Support

For questions or issues:
1. Check the Troubleshooting section above
2. Review backend logs for specific error messages
3. Verify your configuration matches the Setup Instructions
4. Ensure you're using the correct developer key from `.env`

## License

This feature is part of the AgriDirect project.
