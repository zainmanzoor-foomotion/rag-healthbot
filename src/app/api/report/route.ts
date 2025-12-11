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
});

type Report = z.infer<typeof ReportSchema>;


async function saveToDatabase({ filename, summary, medications }: ReportSummary) {
    try {
        await connectDB();

        // Check if a report with the same filename already exists
        const existingReport = await Report.findOne({ filename });
        if (existingReport) {
            console.log("Report with this filename already exists:", filename);
            return existingReport;
        }

        // Create new report
        const report = await Report.create({
            filename,
            summary,
            medications,
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

        const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

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
  ]
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

            let reportData: { summary: string; medications?: { name: string, purpose: string }[] };

            // Try to parse and validate JSON
            try {
                const maybe = JSON.parse(raw);
                const result = ReportSchema.safeParse(maybe);
                if (result.success) {
                    reportData = result.data;
                } else {
                    // Validation failed — treat as fallback
                    console.warn("Validation failed, using fallback text. Errors:", result.error);
                    reportData = { summary: raw };
                }
            } catch (e) {
                // JSON.parse failed — fallback
                console.warn("JSON.parse failed, using fallback text:", e);
                reportData = { summary: raw };
            }

            // Now push to summaries
            summaries.push({ filename: file.name, summary: reportData.summary, medications: reportData.medications! });
            if (reportData.medications!.length > 0) {
                const report = await saveToDatabase({
                    filename: file.name,
                    summary: reportData.summary,
                    medications: reportData.medications!,
                });
                console.log(report)
            }
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
