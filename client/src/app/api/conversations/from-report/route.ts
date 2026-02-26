import { NextResponse } from "next/server";

export const runtime = "nodejs";

function getServerBaseUrl() {
  // Should point to the FastAPI base, including /api
  // Example: http://localhost:8000/api
  return process.env.RAG_HEALTHBOT_SERVER_URL ?? "http://localhost:8000/api";
}

export async function POST(req: Request) {
  try {
    const { reportId } = await req.json();
    if (!reportId) {
      return NextResponse.json({ error: "reportId required" }, { status: 400 });
    }

    const baseUrl = getServerBaseUrl();
    const upstream = await fetch(`${baseUrl}/conversations/from-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reportId }),
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error(e);
    return NextResponse.json({ error: "server" }, { status: 500 });
  }
}
