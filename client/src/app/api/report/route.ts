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
    id?: number | null;
    link_id?: number | null;
    name?: string;
    text?: string;
    dosage?: string | null;
    frequency?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    purpose?: string | null;
    cui?: string | null;
    confidence?: number | null;
    review_status?: string;
};

type OrchestratorDisease = {
    id?: number | null;
    link_id?: number | null;
    name?: string;
    cui?: string | null;
    icd10_code?: string | null;
    severity?: string | null;
    status?: string | null;
    confidence?: number | null;
    review_status?: string;
};

type OrchestratorProcedure = {
    id?: number | null;
    link_id?: number | null;
    name?: string;
    cui?: string | null;
    cpt_code?: string | null;
    date_performed?: string | null;
    body_site?: string | null;
    outcome?: string | null;
    confidence?: number | null;
    review_status?: string;
};

type OrchestratorOutput = {
    report_id?: number;
    summary?: string;
    medications?: OrchestratorMedication[];
    diseases?: OrchestratorDisease[];
    procedures?: OrchestratorProcedure[];
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

const DEFAULT_POLL_TIMEOUT_MS = Number(
    process.env.RAG_HEALTHBOT_POLL_TIMEOUT_MS ?? 600_000
);

function getServerBaseUrl() {
    // Should point to the FastAPI base, including /api
    // Example: http://localhost:8000/api
    return process.env.RAG_HEALTHBOT_SERVER_URL ?? "http://localhost:8000/api";
}

function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollJob(
    baseUrl: string,
    jobId: string,
    timeoutMs = DEFAULT_POLL_TIMEOUT_MS
) {
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
            const diseasesRaw = output?.diseases ?? [];
            const proceduresRaw = output?.procedures ?? [];

            return {
                reportId: reportId != null ? String(reportId) : undefined,
                filename: file_name,
                summary,
                medications: medsRaw.map((m: any) => ({
                    id: m.id ?? null,
                    link_id: m.link_id ?? null,
                    name: String(m.name ?? m.text ?? ""),
                    purpose: String(m.purpose ?? ""),
                    cui: m.cui ?? null,
                    confidence: m.confidence ?? null,
                    review_status: m.review_status ?? "pending_review",
                    is_drug_class: m.is_drug_class ?? false,
                })),
                diseases: diseasesRaw.map((d: any) => ({
                    id: d.id ?? null,
                    link_id: d.link_id ?? null,
                    name: String(d.name ?? ""),
                    cui: d.cui ?? null,
                    icd10_code: d.icd10_code ?? null,
                    severity: d.severity ?? null,
                    status: d.status ?? null,
                    confidence: d.confidence ?? null,
                    review_status: d.review_status ?? "pending_review",
                })),
                procedures: proceduresRaw.map((p: any) => ({
                    id: p.id ?? null,
                    link_id: p.link_id ?? null,
                    name: String(p.name ?? ""),
                    cui: p.cui ?? null,
                    cpt_code: p.cpt_code ?? null,
                    date_performed: p.date_performed ?? null,
                    body_site: p.body_site ?? null,
                    outcome: p.outcome ?? null,
                    confidence: p.confidence ?? null,
                    review_status: p.review_status ?? "pending_review",
                })),
            };
        });

        return NextResponse.json({ summaries });
    } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to summarize reports";
        console.error("/api/report failed:", err);
        return NextResponse.json(
            { error: message },
            { status: 502 }
        );
    }
}
