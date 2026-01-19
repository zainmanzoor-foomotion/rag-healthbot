import { NextResponse } from "next/server";
import { GoogleGenAI } from "@google/genai";
import { z } from "zod";

import { connectDB } from "@/helpers/mongodb";
import Report from "@/schemas/Report";
import { ReportSummary } from "@/types/types";


const MedicationSchema = z.object({
    name: z.string(),
    purpose: z.string(),
});

const ReportSchema = z.object({
    summary: z.string(),
    medications: z.array(MedicationSchema).optional(),
    extractedText: z.string().optional(),
});

type Report = z.infer<typeof ReportSchema>;


async function saveToDatabase({ filename, summary, medications, extractedText }: ReportSummary & { extractedText?: string }) {
    try {
        await connectDB();

        const existingReport = await Report.findOne({ filename });
        if (existingReport) {
            console.log("Report with this filename already exists:", filename);
            return existingReport;
        }
        
        const report = await Report.create({
            filename,
            summary,
            medications,
            extractedText,
        });

        return report;
    } catch (error) {
        console.error("Error saving report:", error);
        throw new Error("Failed to save report");
    }
}


export async function POST(req: Request) {
    try {
        await connectDB();
        const formData = await req.formData();
        const files = formData.getAll("file") as File[];

        if (!files || files.length === 0) {
            return NextResponse.json({ error: "No files uploaded" }, { status: 400 });
        }

        const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY });

        const summaries: ReportSummary[] = [];


                for (const file of files) {
            const arrayBuffer = await file.arrayBuffer();
            const buffer = Buffer.from(arrayBuffer);
            const base64 = buffer.toString("base64");

            const contents = [
                {
                    inlineData: {
                        mimeType: "application/pdf",
                        data: base64,
                    },
                },
                `
You are a medical summarization specialist.
Return a JSON object (not HTML or markdown) summarizing the medical report from the PDF with exactly the following structure:

{
  "summary": "<plain-text summary of patient condition and key findings>",
  "medications": [
    { "name": "<medication name>", "purpose": "<the medication’s purpose / explanation>" }
    ...
    ],
    "extractedText": "<plain-text extracted content from the report suitable for later Q&A; omit PHI if present; keep within ~12000 characters>"
}

Do NOT include any other fields (e.g. dosage, diagnosis, lifestyle advice, signature, etc.).
`
            ];

            const response = await ai.models.generateContent({
                model: "gemini-2.5-flash",
                contents,
            });
            let raw = response.text ?? "";
            if (raw.startsWith("```json")) {
                raw = raw.replace(/^```json\s*/, "");
                raw = raw.replace(/\s*```$/, "");
            }
            raw = raw.trim();

            let reportData: { summary: string; medications?: { name: string, purpose: string }[]; extractedText?: string };

            try {
                const maybe = JSON.parse(raw);
                const result = ReportSchema.safeParse(maybe);
                if (result.success) {
                    reportData = result.data;
                } else {
                    console.warn("Validation failed, using fallback text. Errors:", result.error);
                    reportData = { summary: raw };
                }
            } catch (e) {
                console.warn("JSON.parse failed, using fallback text:", e);
                reportData = { summary: raw };
            }

            const meds = reportData.medications ?? [];
            const extractedText = reportData.extractedText ?? "";

            const report = await saveToDatabase({
                filename: file.name,
                summary: reportData.summary,
                medications: meds,
                extractedText,
            });

            summaries.push({
                reportId: report._id.toString(),
                filename: file.name,
                summary: reportData.summary,
                medications: meds,
            });
        }

        return NextResponse.json({ summaries });
    } catch (err) {
        console.error(err);
        return NextResponse.json(
            { error: "Failed to summarize reports" },
            { status: 500 }
        );
    }
}
