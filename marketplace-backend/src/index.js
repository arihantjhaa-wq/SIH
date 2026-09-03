import app from './app.js'
import dotenv from 'dotenv'
import connectDB from './db/index.js';


dotenv.config({
    path: "./.env",
});

// Startup configuration validation for Developer Access
if (process.env.DEVELOPER_ACCESS_ENABLED === 'true') {
  if (!process.env.DEVELOPER_ACCESS_KEY) {
    console.error("FATAL: DEVELOPER_ACCESS_ENABLED is true but DEVELOPER_ACCESS_KEY is not configured.");
    process.exit(1);
  }
  if (process.env.DEVELOPER_ACCESS_KEY.length < 32) {
    console.error("FATAL: DEVELOPER_ACCESS_KEY must be at least 32 characters long for security.");
    process.exit(1);
  }
  console.log("[SECURITY] Developer access is ENABLED. Ensure this is disabled in production.");
}

const port = process.env.PORT || 7200;

connectDB()
  .then(() =>{
    app.listen(port, () => {
    console.log(`Example app listening on port http://localhost:${port}`)
});
})
  .catch((err)=>{
    console.error("Mongodb connection error", err);
    process.exit(1);
  })