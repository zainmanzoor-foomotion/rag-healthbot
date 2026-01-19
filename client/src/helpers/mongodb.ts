import mongoose from "mongoose";

export const connectDB = async () => {
    try {
        if (mongoose.connection.readyState >= 1) return;

        await mongoose.connect(process.env.MONGODB_URL as string);
        console.log("MongoDB connected");
    } catch (error) {
        console.error("MongoDB connection error:", error);
    }
};
