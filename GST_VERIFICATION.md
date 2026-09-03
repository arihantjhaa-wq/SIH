# GSTIN Verification — Sandbox Integration

## Overview

AgriDirect now integrates real GSTIN (Goods and Services Tax Identification Number) verification using the **Sandbox.co.in** GST API. This allows business customers to verify their GST registration and unlock farmer-direct bulk pricing.

## Features

### For Normal Users (B2B Customers)
- Real-time GSTIN verification with Indian GST portal data
- Displays verified business legal name and trade name
- Shows GSTIN status (Active/Inactive) and taxpayer type
- Unlocks bulk business pricing only after successful verification
- Clear error messages for invalid or inactive GSTINs

### For Developers (Demo Mode)
- Developer Demo GSTIN for testing B2B workflows
- No external API call for demo verification
- Allows developers to test bulk ordering features
- Clearly marked as "Developer Demo" in UI
- Requires authenticated Developer Access session

## Architecture

```
Normal User Flow:
React Frontend
    ↓
POST /api/v1/gst/verify
    ↓
AgriDirect Backend (format validation)
    ↓
Sandbox.co.in GST API
    ↓
AgriDirect Backend (sanitize response)
    ↓
React Frontend (display result)

Developer Flow:
Developer Access Authentication
    ↓
Authenticated __developer__ session
    ↓
POST /api/v1/gst/verify (with isDemoRequest)
    ↓
Backend returns demo identity (NO Sandbox call)
    ↓
React Frontend (B2B access unlocked)
```

## Sandbox API Integration

### Configuration

Environment variables in `marketplace-backend/.env`:
```env
SANDBOX_API_KEY=<your_sandbox_api_key>
SANDBOX_AUTH_TOKEN=<your_sandbox_auth_token>
GST_VERIFICATION_ENABLED=true
```

### API Endpoint Used

- **Base URL**: `https://api.sandbox.co.in`
- **Endpoint**: `GET /gsp/public/gstin/{gstin}`
- **Method**: GET
- **Headers**:
  - `x-api-key`: Sandbox API key
  - `Authorization`: Sandbox auth token
  - `x-api-version`: 1.0
  - `Content-Type`: application/json
- **Timeout**: 8 seconds

### Response Handling

The backend processes Sandbox API responses and returns one of 5 distinct states:

1. **VERIFIED** - GSTIN found and active in GST portal
2. **NOT_VERIFIED** - GSTIN not found or inactive
3. **FORMAT_INVALID** - GSTIN doesn't match Indian GSTIN format
4. **PROVIDER_UNAVAILABLE** - Sandbox API temporarily unavailable
5. **VERIFICATION_DISABLED** - GST verification disabled in configuration

## Backend Implementation

### Files Created/Modified

1. **`marketplace-backend/src/controllers/gst.controller.js`** (NEW)
   - `verifyGstin()` - Main verification controller
   - Format validation using regex
   - Developer demo authentication check
   - Sandbox API integration with timeout
   - Response sanitization

2. **`marketplace-backend/src/routes/gst.rout.js`** (NEW)
   - `POST /verify` route

3. **`marketplace-backend/src/app.js`** (MODIFIED)
   - Registered GST routes: `app.use("/api/v1/gst", gstRoutes)`

4. **`marketplace-backend/.env`** (MODIFIED)
   - Added Sandbox credentials
   - Added GST_VERIFICATION_ENABLED flag

5. **`marketplace-backend/.env.example`** (MODIFIED)
   - Added placeholder configuration

### Verification Logic

```javascript
1. Check if GST_VERIFICATION_ENABLED === 'true'
   ↓ No → Return VERIFICATION_DISABLED

2. Validate request body (gstin field exists and is string)
   ↓ Invalid → Return FORMAT_INVALID

3. Normalize GSTIN (trim + uppercase)

4. Validate format: /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/
   ↓ Invalid → Return FORMAT_INVALID (NO Sandbox call)

5. Check authenticated user
   ↓ Is __developer__ + demo request?
      ↓ Yes → Return VERIFIED with isDemo: true
      ↓ No → Continue

6. Check Sandbox credentials configured
   ↓ Missing → Return PROVIDER_UNAVAILABLE

7. Call Sandbox API with 8-second timeout

8. Parse response:
   - 200 OK → Return VERIFIED with sanitized data
   - 404/400 → Return NOT_VERIFIED
   - 5xx/timeout/error → Return PROVIDER_UNAVAILABLE
```

## Frontend Implementation

### Files Created/Modified

1. **`frontend/src/services/gstService.js`** (NEW)
   - `verifyGstinApi()` - API service wrapper

2. **`frontend/src/pages/ConsumerMarketplace.jsx`** (MODIFIED)
   - Added GST verification state management
   - Added verification UI with status indicators
   - Added developer demo button
   - Replaced client-side validation with server verification
   - Business pricing unlocked only on VERIFIED status

### UI States

**Verifying (Loading)**
```
[Input: 27AAACW7823G1ZV] [Verifying...]
⟳ Verifying with GST portal...
```

**Verified (Success)**
```
[Input: 27AAACW7823G1ZV] [Verify]
✓ GSTIN Verified
  WIPRO LIMITED
  Trading as: WIPRO LIMITED
  Status: Active • Regular
```

**Developer Demo**
```
[Input: 07AAAAA0000A1Z5] [Verify]
✓ GSTIN Verified (Developer Demo)
  AgriDirect Developer Demo Enterprise
  Trading as: AgriDirect Demo Agro Supplies
  Status: Active • Regular
```

**Not Verified (Invalid)**
```
[Input: 99AAAAA9999A9Z9] [Verify]
⚠ GSTIN not found or inactive with tax authority.
```

**Format Invalid**
```
[Input: ABC123] [Verify]
⚠ Invalid GSTIN format. Must be 15 alphanumeric
  characters (e.g. 27AAACW7823G1ZV).
```

**Provider Unavailable**
```
[Input: 27AAACW7823G1ZV] [Verify]
⚠ GST verification service is temporarily unavailable.
  [Retry verification]
```

## Developer Demo Mode

### How It Works

1. User authenticates via Developer Access (existing feature)
2. Backend creates `__developer__` user session
3. User navigates to Consumer Marketplace → Business mode
4. Developer sees "Use Developer Demo GSTIN" button
5. Clicking button sends verification request with `isDemoRequest: true`
6. Backend checks if authenticated user is `__developer__`
7. If yes, returns VERIFIED with demo data (NO Sandbox call)
8. Frontend displays demo business identity with "(Developer Demo)" badge
9. Business pricing unlocked for demonstration
10. Logout removes developer session and demo access

### Demo GSTIN

- **Demo GSTIN**: `07AAAAA0000A1Z5`
- **Legal Name**: AgriDirect Developer Demo Enterprise
- **Trade Name**: AgriDirect Demo Agro Supplies
- **Status**: Active
- **Type**: Regular
- **isDemo flag**: true

### Security

✅ **Normal users CANNOT access demo mode**
- Backend verifies authenticated session is `__developer__`
- Frontend flag `isDemoRequest` alone is NOT sufficient
- JWT token must be valid and belong to developer user

✅ **Demo GSTIN never sent to Sandbox**
- No external API call for developer demo
- Demo verification handled entirely by backend

✅ **Session-based access**
- Developer logout terminates demo access
- Demo access requires active developer authentication

## Security Controls

### Secrets Protection
- ✅ Sandbox API key stored server-side only
- ✅ Sandbox auth token stored server-side only
- ✅ No secrets in frontend source code
- ✅ No secrets in frontend bundle (verified)
- ✅ No secrets in Git repository
- ✅ No secrets logged to console

### Authentication & Authorization
- ✅ Developer demo requires authenticated `__developer__` session
- ✅ Backend validates JWT token
- ✅ Backend determines developer status (not frontend)
- ✅ Normal users cannot bypass verification
- ✅ Frontend cannot forge developer status

### Request Validation
- ✅ GSTIN format validated before API call
- ✅ Input sanitized (trim + uppercase)
- ✅ Type checking (must be string)
- ✅ Length validation (15 characters)
- ✅ Regex pattern validation

### Error Handling
- ✅ Safe error messages (no credential exposure)
- ✅ Timeout protection (8-second limit)
- ✅ Provider unavailable vs invalid GSTIN distinction
- ✅ Network errors handled gracefully

### Compatibility
- ✅ Existing authentication preserved
- ✅ Existing Developer Access preserved
- ✅ Normal Login/Register unchanged
- ✅ Pricing Engine untouched
- ✅ Rate limiting preserved

## Testing

### Test Results

All 10 tests passed:

1. ✓ Empty GSTIN → FORMAT_INVALID
2. ✓ Invalid format (too short) → FORMAT_INVALID
3. ✓ Invalid format (wrong structure) → FORMAT_INVALID
4. ✓ Valid format, lowercase → Normalized and processed
5. ✓ Valid format with whitespace → Trimmed and processed
6. ✓ Valid GSTIN (Sandbox test) → Backend response received
7. ✓ Developer demo GSTIN (unauthenticated) → NOT auto-verified
8. ✓ Developer demo GSTIN (with developer auth) → VERIFIED with isDemo=true
9. ✓ GST_VERIFICATION_ENABLED → Configured correctly
10. ✓ Sandbox credentials → Configured correctly

### Manual Testing

#### Test Valid GSTIN (Normal User)
```bash
# 1. Start backend
cd marketplace-backend
npm run dev

# 2. Start frontend
cd frontend
npm run dev

# 3. Browser: http://localhost:5173
# 4. Register/Login as normal user
# 5. Select "I'm a Consumer" → "Business"
# 6. Enter GSTIN: 27AAACW7823G1ZV
# 7. Click "Verify"
# 8. Observe: Verification request sent to backend → Sandbox API
# 9. Result: VERIFIED or NOT_VERIFIED or PROVIDER_UNAVAILABLE
```

#### Test Developer Demo (Developer)
```bash
# 1. Browser: http://localhost:5173
# 2. Click "Developer Access" link
# 3. Enter developer key from marketplace-backend/.env
# 4. Authenticate successfully
# 5. Select "I'm a Consumer" → "Business"
# 6. Click "Use Developer Demo GSTIN"
# 7. Observe: Demo GSTIN auto-populated and verified
# 8. Result: VERIFIED with "Developer Demo" badge
# 9. Legal name: "AgriDirect Developer Demo Enterprise"
# 10. Business pricing unlocked
```

## Usage

### For End Users

1. Register or login to AgriDirect
2. Select "I'm a Consumer"
3. Toggle to "Business" mode
4. Enter your 15-character GSTIN
5. Click "Verify"
6. Wait for verification (usually < 2 seconds)
7. Once verified, business bulk pricing unlocks
8. Shop farmer-direct products at wholesale rates

### For Developers

1. Authenticate via Developer Access
2. Navigate to Consumer Marketplace
3. Select "Business" mode
4. Click "Use Developer Demo GSTIN"
5. Demo business identity automatically verified
6. Test B2B workflows without real GSTIN
7. Browse bulk-order listings
8. Test checkout flow with business pricing

### For Administrators

**Enable/Disable GST Verification:**
```bash
# Edit marketplace-backend/.env
GST_VERIFICATION_ENABLED=true  # or false
```

**Configure Sandbox Credentials:**
```bash
# Edit marketplace-backend/.env
SANDBOX_API_KEY=your_sandbox_api_key
SANDBOX_AUTH_TOKEN=your_sandbox_auth_token
```

**Monitor Logs:**
```bash
# Backend logs show verification attempts
[GST] GSTIN 27AAACW7823G1ZV verified successfully via Sandbox
[GST] GSTIN 99XXXXX9999X9Z9 not found in GST portal
[GST] Developer demo verification granted for 07AAAAA0000A1Z5
```

## API Reference

### POST /api/v1/gst/verify

Verify a GSTIN with the GST portal.

**Request:**
```json
{
  "gstin": "27AAACW7823G1ZV",
  "isDemoRequest": false  // optional, true for developer demo
}
```

**Response (VERIFIED):**
```json
{
  "statusCode": 200,
  "success": true,
  "message": "GSTIN verified",
  "data": {
    "status": "VERIFIED",
    "data": {
      "gstin": "27AAACW7823G1ZV",
      "legalName": "WIPRO LIMITED",
      "tradeName": "WIPRO LIMITED",
      "gstinStatus": "Active",
      "taxpayerType": "Regular",
      "isDemo": false
    },
    "message": "GSTIN verified successfully."
  }
}
```

**Response (NOT_VERIFIED):**
```json
{
  "statusCode": 200,
  "success": true,
  "message": "GSTIN not verified",
  "data": {
    "status": "NOT_VERIFIED",
    "message": "GSTIN not found or inactive with tax authority."
  }
}
```

**Response (FORMAT_INVALID):**
```json
{
  "statusCode": 200,
  "success": true,
  "message": "Invalid GSTIN format",
  "data": {
    "status": "FORMAT_INVALID",
    "message": "Invalid GSTIN format. Must be 15 alphanumeric characters (e.g. 27AAACW7823G1ZV)."
  }
}
```

**Response (PROVIDER_UNAVAILABLE):**
```json
{
  "statusCode": 200,
  "success": true,
  "message": "Provider unavailable",
  "data": {
    "status": "PROVIDER_UNAVAILABLE",
    "message": "GST verification service is temporarily unavailable. Please try again later."
  }
}
```

**Response (VERIFICATION_DISABLED):**
```json
{
  "statusCode": 200,
  "success": true,
  "message": "GST verification is disabled",
  "data": {
    "status": "VERIFICATION_DISABLED",
    "message": "GST verification is currently disabled."
  }
}
```

## Troubleshooting

### "GST verification service is temporarily unavailable"
**Cause**: Sandbox API timeout, network error, or 5xx response
**Solution**: 
- Check internet connectivity
- Verify Sandbox API status
- Retry verification after a few seconds
- Check backend logs for detailed error

### "Invalid GSTIN format"
**Cause**: GSTIN doesn't match 15-character Indian GSTIN pattern
**Solution**:
- Verify GSTIN is exactly 15 characters
- Check format: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + "Z" + 1 alphanumeric
- Example: 27AAACW7823G1ZV

### "GSTIN not found or inactive"
**Cause**: GSTIN not registered with GST portal or registration cancelled
**Solution**:
- Double-check GSTIN with business registration documents
- Verify GSTIN is active on official GST portal
- Contact tax consultant if GSTIN should be active

### Developer Demo Not Working
**Cause**: Not authenticated as developer
**Solution**:
- Logout and re-authenticate via Developer Access
- Verify developer key in marketplace-backend/.env
- Check browser console for authentication errors
- Verify `__developer__` user in database

### Sandbox API Credentials Invalid
**Cause**: API key or auth token incorrect/expired
**Solution**:
- Verify credentials in marketplace-backend/.env
- Contact Sandbox.co.in for credential refresh
- Check for typos in environment variables
- Restart backend after updating credentials

## Production Deployment

### Checklist

- [ ] Obtain production Sandbox API credentials
- [ ] Update `SANDBOX_API_KEY` and `SANDBOX_AUTH_TOKEN` in production `.env`
- [ ] Set `GST_VERIFICATION_ENABLED=true`
- [ ] Set `DEVELOPER_ACCESS_ENABLED=false` in production
- [ ] Verify `.env` is in `.gitignore`
- [ ] Test GSTIN verification with production Sandbox endpoint
- [ ] Monitor backend logs for verification failures
- [ ] Set up alerting for high failure rates
- [ ] Configure rate limiting if Sandbox has usage limits

### Environment Variables

**Development:**
```env
SANDBOX_API_KEY=<your_sandbox_api_key>
SANDBOX_AUTH_TOKEN=<your_sandbox_auth_token>
GST_VERIFICATION_ENABLED=true
DEVELOPER_ACCESS_ENABLED=true
```

**Production:**
```env
SANDBOX_API_KEY=<production_api_key>
SANDBOX_AUTH_TOKEN=<production_auth_token>
GST_VERIFICATION_ENABLED=true
DEVELOPER_ACCESS_ENABLED=false
```

## Known Limitations

1. **Sandbox API Rate Limits**: Check Sandbox.co.in documentation for API usage limits
2. **Network Dependency**: Requires internet connectivity to verify GSTINs
3. **Provider Downtime**: GST verification unavailable if Sandbox API is down
4. **Real-time Data**: GSTIN status reflects Sandbox's last sync with GST portal
5. **Demo Mode**: Only accessible to authenticated developers (by design)

## Future Enhancements

- [ ] Cache verified GSTINs to reduce API calls
- [ ] Add GSTIN verification history/audit log
- [ ] Implement webhook for GSTIN status changes
- [ ] Add bulk GSTIN verification API
- [ ] Support for additional GST-related data (filing status, etc.)
- [ ] Rate limiting for verification endpoint
- [ ] Monitoring dashboard for verification metrics

## Support

For issues or questions:
1. Check backend logs: `marketplace-backend/` console output
2. Check browser console: Network tab for API responses
3. Review this documentation
4. Test with known valid GSTIN: 27AAACW7823G1ZV
5. Verify Sandbox credentials are configured correctly

---

**Implementation Date**: September 3, 2026  
**Sandbox API Version**: 1.0  
**Status**: ✅ Fully Implemented and Tested
