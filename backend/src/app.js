import express from 'express'
import cors from 'cors'
import cookieParser from 'cookie-parser'

const app = express()

//basic Configuration
app.use(express.json({limit:"16kb"}));
app.use(express.urlencoded({extended:true , limit: "16kb"}));
// Serves both static assets and uploaded product images (uploads/products/...)
app.use(express.static("public"));
app.use(cookieParser());

//CORS Configuration
app.use(cors({
    origin: process.env.CORS_ORIGIN?.split(",") || ["http://localhost:5173", "http://127.0.0.1:5173"],
    credentials: true,
    methods: ["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allowedHeaders: ["Content-Type","Authorization"],
}));

import healthcheackRoutes from './routes/healthcheack.rout.js'
app.use("/api/v1/healthcheck", healthcheackRoutes)

import  authRoutes from './routes/auth.rout.js'
app.use("/api/v1/auth" , authRoutes);

import productRoutes from './routes/product.rout.js'
app.use("/api/v1/products" , productRoutes);

import gstRoutes from './routes/gst.rout.js'
app.use("/api/v1/gst", gstRoutes);

import orderRoutes from './routes/order.rout.js'
app.use("/api/v1/orders", orderRoutes);

import forecastRoutes from './routes/forecast.rout.js'
app.use("/api/v1/forecast", forecastRoutes);

// Global Error Handler
import { ApiError } from './utils/api-error.js';

app.use((err, req, res, next) => {
    // Multer-specific errors → proper HTTP status codes
    if (err.code === "INVALID_FILE_TYPE") {
        return res.status(400).json({
            statusCode: 400,
            message: err.message || "Unsupported file type",
            success: false,
            errors: [],
            data: null,
        });
    }
    if (err.code === "LIMIT_FILE_SIZE") {
        return res.status(413).json({
            statusCode: 413,
            message: "File too large. Maximum size is 5 MB.",
            success: false,
            errors: [],
            data: null,
        });
    }

    if (err instanceof ApiError) {
        return res.status(err.statusCode).json({
            statusCode: err.statusCode,
            message: err.message,
            success: false,
            errors: err.errors,
            data: null,
        });
    }

    return res.status(500).json({
        statusCode: 500,
        message: err.message || "Internal Server Error",
        success: false,
        errors: [],
        data: null,
    });
});

export default app;