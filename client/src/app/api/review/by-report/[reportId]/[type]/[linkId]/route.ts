import { NextRequest, NextResponse } from "next/server";

const SERVER_BASE =
  process.env.RAG_HEALTHBOT_SERVER_URL ?? "http://localhost:8000/api";

export async function PATCH(
  req: NextRequest,
  {
    params,
  }: { params: Promise<{ reportId: string; type: string; linkId: string }> }
) {
  const { reportId, type, linkId } = await params;
  const body = await req.json().catch(() => ({}));

  try {
    const res = await fetch(
      `${SERVER_BASE}/review/by-report/${reportId}/${type}/${linkId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );

    const raw = await res.text();
    let parsed: unknown = null;
    if (raw) {
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = raw;
      }
    }

    if (!res.ok) {
      return NextResponse.json(
        {
          error: "Upstream review update request failed",
          upstreamStatus: res.status,
          detail: parsed,
        },
        { status: res.status }
      );
    }

    return NextResponse.json(parsed, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Failed to reach review update upstream",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 502 }
    );
  }
}
