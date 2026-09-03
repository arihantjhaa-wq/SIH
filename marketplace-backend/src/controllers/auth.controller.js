import { User } from "../models/user.model.js";
import { ApiResponse } from "../utils/api-responce.js";
import { ApiError } from "../utils/api-error.js";
import { asyncHandler } from "../utils/async-handler.js";
import { emailVerificationMailgenContent, sendEmail } from "../utils/mail.js";
import { clearDeveloperAccessRateLimit } from "../middlewares/rate-limit.middleware.js";
import crypto from "crypto";


const registerUser = asyncHandler(async (req, res) => {

  const { email, username, password, role } = req.body;


  const existedUser = await User.findOne({
    $or: [{ username }, { email }],
  });


  if (existedUser?.email === email) {
    throw new ApiError(409, "Email already registered");
  }

  if (existedUser?.username === username) {
    throw new ApiError(409, "Username already taken");
  }


  const user = await User.create({
    email,
    password,
    username,
    isEmailVerified: false,
  });

  const { unHashedToken, hashedToken, tokenExpiry } =
    user.generateTemporaryToken();

  user.emailVerificationToken = hashedToken;
  user.emailVerificationExpiry = tokenExpiry;

  await user.save({ validateBeforeSave: false });

  await sendEmail({
    email: user?.email,
    subject: "Please verify your email",
    mailgenContent: emailVerificationMailgenContent(
      user.username,
      `${req.protocol}://${req.get("host")}/api/v1/auth/verify-email/${unHashedToken}`,
    ),
  });

  const createdUser = await User.findById(user._id).select(
    "-password -refreshToken -emailVerificationToken -emailVerificationExpiry",
  );

  if (!createdUser) {
    throw new ApiError(500, "Something went wrong while registering a user");
  }

  return res
    .status(201)
    .json(
      new ApiResponse(
        200,
        { user: createdUser },
        "User registered successfully and verification email has been sent on your email",
      ),
    );
});

const login = asyncHandler(async (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    throw new ApiError(400, "Username and password are required");
  }

  const user = await User.findOne({ username });

  if (!user) {
    throw new ApiError(404, "User not found in database, please register first");
  }

  const isPasswordValid = await user.isPasswordCorrect(password);

  if (!isPasswordValid) {
    throw new ApiError(401, "Incorrect password, please try again");
  }

  const accessToken = user.generateAccessToken();
  const refreshToken = user.generateRefreshToken();

  user.refreshToken = refreshToken;
  await user.save({ validateBeforeSave: false });

  const loggedInUser = await User.findById(user._id).select(
    "-password -refreshToken -emailVerificationToken -emailVerificationExpiry"
  );

  const options = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: process.env.NODE_ENV === "production" ? "none" : "lax",
  };

  return res
    .status(200)
    .cookie("accessToken", accessToken, options)
    .cookie("refreshToken", refreshToken, options)
    .json(
      new ApiResponse(
        200,
        {
          user: loggedInUser,
          accessToken,
          refreshToken,
        },
        "User logged in successfully"
      )
    );
});

const logout = asyncHandler(async (req, res) => {
  await User.findByIdAndUpdate(
    req.user._id,
    {
      $set: {
        refreshToken: "",
      },
    },
    {
      new: true,
    },
  );

  const options = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: process.env.NODE_ENV === "production" ? "none" : "lax",
  };

  return res
    .status(200)
    .clearCookie("accessToken", options)
    .clearCookie("refreshToken", options)
    .json(new ApiResponse(200, {}, "User logged out"));
    
});

const verifyEmail = asyncHandler(async (req ,res) => {

  const {verificationToken} = req.params;

  if(!verificationToken){
    throw new ApiError(401 , "Email Verification Token is Missing");
  }

  const hashedToken = crypto
    .createHash("sha256")
    .update(verificationToken)
    .digest("hex");

  const user = await User.findOne(
    {
      emailVerificationToken: hashedToken,
      emailVerificationExpiry: { $gt: Date.now() },
    }
  );

  if(!user){
    throw new ApiError(400, "Token is Invalid")
  }

  user.emailVerificationToken = undefined;
  user.emailVerificationExpiry = undefined;

  user.isEmailVerified = true;

  await user.save({ validateBeforeSave: false });

  res
    .status(200)
    .json(
      new ApiResponse(
        200,
        {
          isEmailVerified : true
        },
        "Email Verivied "
      )
    )

});

const getCurrentUser = asyncHandler(async (req, res) => {
  return res
    .status(200)
    .json(new ApiResponse(200, { user: req.user }, "Current user fetched successfully"));
});

const developerAccess = asyncHandler(async (req, res) => {
  // 1. Check if developer access is enabled
  if (process.env.DEVELOPER_ACCESS_ENABLED !== 'true') {
    throw new ApiError(403, "Developer access is currently unavailable");
  }

  // 2. Validate environment configuration
  if (!process.env.DEVELOPER_ACCESS_KEY || process.env.DEVELOPER_ACCESS_KEY.length < 32) {
    console.error("SECURITY: Developer access enabled but key is missing or weak");
    throw new ApiError(500, "Server configuration error");
  }

  // 3. Extract and validate key from request body
  const { developerKey } = req.body;

  if (!developerKey || typeof developerKey !== 'string') {
    console.warn(`[AUTH] Developer access attempt failed: missing or invalid key type at ${new Date().toISOString()}`);
    throw new ApiError(400, "Please enter your developer key");
  }

  const trimmedKey = developerKey.trim();
  if (!trimmedKey) {
    console.warn(`[AUTH] Developer access attempt failed: empty key at ${new Date().toISOString()}`);
    throw new ApiError(400, "Please enter your developer key");
  }

  // 4. Constant-time comparison to prevent timing attacks
  const expectedKey = process.env.DEVELOPER_ACCESS_KEY;

  if (trimmedKey.length !== expectedKey.length) {
    console.warn(`[AUTH] Developer access attempt failed: invalid key at ${new Date().toISOString()}`);
    throw new ApiError(401, "Invalid developer key");
  }

  // Use crypto.timingSafeEqual for constant-time comparison
  const keyBuffer = Buffer.from(trimmedKey, 'utf8');
  const expectedBuffer = Buffer.from(expectedKey, 'utf8');

  let isValid;
  try {
    isValid = crypto.timingSafeEqual(keyBuffer, expectedBuffer);
  } catch (err) {
    console.warn(`[AUTH] Developer access attempt failed: comparison error at ${new Date().toISOString()}`);
    throw new ApiError(401, "Invalid developer key");
  }

  if (!isValid) {
    console.warn(`[AUTH] Developer access attempt failed: invalid key at ${new Date().toISOString()}`);
    throw new ApiError(401, "Invalid developer key");
  }

  // 5. Clear rate limit on successful verification
  clearDeveloperAccessRateLimit(req);

  // 6. Create or fetch a dedicated developer user
  let devUser = await User.findOne({ username: '__developer__' });

  if (!devUser) {
    // Create a special developer user (no password, email verified)
    devUser = await User.create({
      username: '__developer__',
      email: 'developer@internal.local',
      password: crypto.randomBytes(32).toString('hex'), // Random, never used
      isEmailVerified: true,
    });
    console.log(`[AUTH] Created __developer__ user at ${new Date().toISOString()}`);
  }

  // 7. Generate tokens using existing auth mechanism
  const accessToken = devUser.generateAccessToken();
  const refreshToken = devUser.generateRefreshToken();

  devUser.refreshToken = refreshToken;
  await devUser.save({ validateBeforeSave: false });

  const options = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: process.env.NODE_ENV === "production" ? "none" : "lax",
  };

  console.log(`[AUTH] Developer access granted at ${new Date().toISOString()}`);

  // 8. Return authenticated session (same structure as normal login)
  return res
    .status(200)
    .cookie("accessToken", accessToken, options)
    .cookie("refreshToken", refreshToken, options)
    .json(
      new ApiResponse(
        200,
        {
          user: {
            _id: devUser._id,
            username: devUser.username,
            email: devUser.email,
            isEmailVerified: devUser.isEmailVerified,
            isDeveloper: true, // Client-side flag for UI
          },
          accessToken,
          refreshToken,
        },
        "Developer access granted"
      )
    );
});

export { registerUser , login , logout, verifyEmail, getCurrentUser, developerAccess};
