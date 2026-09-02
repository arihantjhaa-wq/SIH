import express from 'express'
import cors from 'cors'

const app = express()

//basic Configuration
app.use(express.json({limit:"16kb"}));
app.use(express.urlencoded({extended:true , limit: "16kb"}));
app.use(express.static("public"));

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

// import todoRoutes from './routes/todo.router.js'
// app.use("/api/v1/task", todoRoutes);

// Global Error Handler
import { ApiError } from './utils/api-error.js';

app.use((err, req, res, next) => {
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