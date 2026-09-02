import mongoose, { Schema } from "mongoose";
import jsonwebtoken from 'jsonwebtoken';
import bcrypt from 'bcrypt';
import crypto from 'crypto';

const userSchema = new Schema(
    {
        username: {
            type: String,
            required: true,
            unique: true,
            lowecase: true,
            trim: true,
            index: true
        },
        email: {
            type: String,
            required: true,
            unique: true,
            lowercase: true,
            trim: true
        },
        fullName: {
            type: String,
            trim: true
        },
        password: {
            type: String,
            required: [true, 'Password is Required']
        },
        isEmailVerified: {
            type: Boolean,
            default: false
        },
        refreshToken: {
            type: String
        },
        forgotPasswordToken: {
            type: String
        },
        forgotPasswordExpiry: {
            type: Date
        },
        emailVerificationToken: {
            type: String
        },
        emailVerificationExpiry: {
            type: Date
        }
    },
    {
        timestamps: true
    }
)

userSchema.pre("save", async function () {
  if (!this.isModified("password")) return null;

  this.password = await bcrypt.hash(this.password, 10);
});

userSchema.methods.isPasswordCorrect = async function(enteredPassword) {
    return await bcrypt.compare(enteredPassword, this.password)
}

userSchema.methods.generateRefreshToken = function () {
    return jsonwebtoken.sign(
        { _id: this._id },
        process.env.REFRESH_TOKEN_SECRET,
        { expiresIn: process.env.REFRESH_TOKEN_EXPIRY }
    );
};

userSchema.methods.generateAccessToken = function () {
    return jsonwebtoken.sign(
        {
            _id: this._id,
            email: this.email,
            username: this.username
        },
        process.env.ACCESS_TOKEN_SECRET,
        { expiresIn: process.env.ACCESS_TOKEN_EXPIRY }
    );
};
 

userSchema.methods.generateTemporaryToken = function() {
    const unHashedToken = crypto.randomBytes(20).toString("hex")

    const hashedToken = crypto
        .createHash("sha256")
        .update(unHashedToken)
        .digest("hex")

    const tokenExpiry = Date.now() + (20*60*1000) //20 mins
    return {unHashedToken, hashedToken, tokenExpiry}
}


export const User = mongoose.model("User",userSchema);
