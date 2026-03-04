import { NextRequest, NextResponse } from "next/server";

const SERVER_BASE =
  process.env.RAG_HEALTHBOT_SERVER_URL ?? "http://localhost:8000/api";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ reportId: string }> }
) {
  const { reportId } = await params;
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status");

  const url = new URL(`${SERVER_BASE}/review/by-report/${reportId}`);
  if (status) {
    url.searchParams.set("status", status);
  }

  try {
    const res = await fetch(url.toString(), { cache: "no-store" });
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
          error: "Upstream review queue request failed",
          upstreamStatus: res.status,
          detail: parsed,
        },
        { status: res.status }
      );
    }

    return NextResponse.json(Array.isArray(parsed) ? parsed : [], {
      status: res.status,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Failed to reach review queue upstream",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 502 }
    );
  }
}
