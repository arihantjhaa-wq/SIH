import mongoose from 'mongoose';

const connectDB = async () => {
   try{
        await mongoose.connect(process.env.MONGODB_URI);
        console.log("Dtabace Conection done Succesfuly Done")
   }catch(error){
        console.error("MongoDB Connection Failed ", error);
        process.exit(1);
   }
}

export default connectDB;