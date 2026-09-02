import { User } from "../models/user.model.js";
import { ApiResponse } from "../utils/api-responce.js";
import { ApiError } from "../utils/api-error.js";
import { asyncHandler } from "../utils/async-handler.js";
import { emailVerificationMailgenContent, sendEmail } from "../utils/mail.js";
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
      `${req.protocol}://${req.get("host")}/api/v1/users/verify-email/${unHashedToken}`,
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

export { registerUser , login , logout, verifyEmail};
