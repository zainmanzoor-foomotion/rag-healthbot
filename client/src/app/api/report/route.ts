import { NextResponse } from "next/server";
import { ReportSummary } from "@/types/types";

export const runtime = "nodejs";

type UploadItem = {
    file_name: string;
    mime_type: string;
    file_content: string; // base64
};

type UploadResponse = {
    jobs: Array<{ job_id: string; file_name: string }>;
};

type OrchestratorMedication = {
    name?: string;
    text?: string;
    dosage?: string | null;
    frequency?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    purpose?: string | null;
};

type OrchestratorOutput = {
    report_id?: number;
    summary?: string;
    medications?: OrchestratorMedication[];
};

type OrchestratorResult = {
    status?: string;
    reason_code?: string;
    output?: OrchestratorOutput | null;
};

type JobStatusResponse = {
    job_id: string;
    status: string;
    stage?: string | null;
    result?: OrchestratorResult;
    error?: string | null;
};

function getServerBaseUrl() {
    // Should point to the FastAPI base, including /api
    // Example: http://localhost:8000/api
    return process.env.RAG_HEALTHBOT_SERVER_URL ?? "http://localhost:8000/api";
}

function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollJob(baseUrl: string, jobId: string, timeoutMs = 120_000) {
    const started = Date.now();
    while (true) {
        const res = await fetch(`${baseUrl}/report/jobs/${jobId}`);
        if (!res.ok) {
            const text = await res.text().catch(() => "");
            throw new Error(`Failed to poll job ${jobId}: ${res.status} ${text}`);
        }
        const data = (await res.json()) as JobStatusResponse;

        if (data.status === "failed") {
            throw new Error(data.error ?? `Job ${jobId} failed`);
        }
        if (data.status === "finished") {
            return data;
        }

        if (Date.now() - started > timeoutMs) {
            throw new Error(`Timed out waiting for job ${jobId}`);
        }
        await sleep(1000);
    }
}


export async function POST(req: Request) {
    try {
        const formData = await req.formData();
        const files = formData.getAll("file") as File[];

        if (!files || files.length === 0) {
            return NextResponse.json({ error: "No files uploaded" }, { status: 400 });
        }

        const baseUrl = getServerBaseUrl();

        const uploadItems: UploadItem[] = [];
        for (const file of files) {
            const arrayBuffer = await file.arrayBuffer();
            const buffer = Buffer.from(arrayBuffer);
            const base64 = buffer.toString("base64");

            uploadItems.push({
                file_name: file.name,
                mime_type: file.type || "application/pdf",
                file_content: base64,
            });
        }

        const uploadRes = await fetch(`${baseUrl}/report`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ files: uploadItems }),
        });

        if (!uploadRes.ok) {
            const text = await uploadRes.text().catch(() => "");
            return NextResponse.json(
                { error: `FastAPI upload failed: ${uploadRes.status} ${text}` },
                { status: 502 }
            );
        }

        const uploadData = (await uploadRes.json()) as UploadResponse;
        const jobs = uploadData.jobs ?? [];

        const jobResults = await Promise.all(
            jobs.map(async (j) => {
                const status = await pollJob(baseUrl, j.job_id);
                return { file_name: j.file_name, job_id: j.job_id, status };
            })
        );

        const summaries: ReportSummary[] = jobResults.map(({ file_name, status }) => {
            const orchestratorResult = status.result;
            const output = orchestratorResult?.output;
            const reportId = output?.report_id;
            const summary = output?.summary ?? "";
            const medsRaw = output?.medications ?? [];

            return {
                reportId: reportId != null ? String(reportId) : undefined,
                filename: file_name,
                summary,
                medications: medsRaw.map((m) => ({
                    name: String(m.name ?? m.text ?? ""),
                    purpose: String(m.purpose ?? ""),
                })),
            };
        });

        return NextResponse.json({ summaries });
    } catch (err) {
        console.error(err);
        return NextResponse.json(
            { error: "Failed to summarize reports" },
            { status: 500 }
        );
    }
}
