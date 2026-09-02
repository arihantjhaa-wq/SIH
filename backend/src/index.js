import app from './app.js'
import dotenv from 'dotenv'
import connectDB from './db/index.js';


dotenv.config({
    path: "./.env",
});

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