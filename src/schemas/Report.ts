import mongoose, { Schema, Document } from "mongoose";
import { Medication } from "@/types/types";


export interface IReport extends Document {
    filename: string;
    summary: string;
    medications: Medication[];
}

const MedicationsSchema = new Schema<Medication>({
    name: { type: String, required: true },
    purpose: { type: String, required: true },
})

const ReportSchema = new Schema<IReport>({
    filename: { type: String, required: true },
    summary: { type: String, required: true },
    medications: { type: [MedicationsSchema], default: [] },
},
    { timestamps: true }
)

export default mongoose.models.Report ||
    mongoose.model<IReport>("Report", ReportSchema);
