// import { asyncHandler } from "../utils/async-handler.js";
// import { ApiError } from "../utils/api-error.js";
// import { User } from "../models/user.model.js";
// import jwt from 'jsonwebtoken';

// const verifyJWT =asyncHandler( (req, res, next) => {

//     const token = req.cookies?.accessToken || req.header("Authorization")?.replace("Bearer ", "");
//     try {
//         if (!token) {
//             throw new ApiError(401, "Unauthirized Access , Access Denide");
//         }
//         const decodedToken = jwt.verify(token, process.env.ACCESS_TOKEN_SECRET);
//         console.log(decodedToken);
//         const user = User.findById(decodedToken?._id).select("-password -refreshToken -emailVerificationToken -emailVerificationExpiry");
//         if (!user) {
//             throw new ApiError(401, "Invalide AccessToken , Access Denied");
//         }

//         res.user = user;
//         next();

//     } catch (error) {
//         throw new ApiError(401 ,"Invalid AccessToken");
//         next();
//     }

// });

// export {verifyJWT};


import { asyncHandler } from "../utils/async-handler.js";
import { ApiError } from "../utils/api-error.js";
import { User } from "../models/user.model.js";
import jwt from "jsonwebtoken";

const verifyJWT = asyncHandler(async (req, res, next) => {

    const token =
        req.cookies?.accessToken ||
        req.header("Authorization")?.replace("Bearer ", "");

    if (!token) {
        throw new ApiError(401, "Unauthorized Access, Access Denied");
    }

    try {
        const decodedToken = jwt.verify(
            token,
            process.env.ACCESS_TOKEN_SECRET
        );

        const user = await User.findById(decodedToken?._id).select(
            "-password -refreshToken -emailVerificationToken -emailVerificationExpiry"
        );

        console.log("User:", user); 

        if (!user) {
            throw new ApiError(401, "Invalid AccessToken, User not found");
        }

        req.user = user;

        next();

    } catch (error) {
        throw new ApiError(401, "Invalid or Expired AccessToken");
    }
});

export { verifyJWT };