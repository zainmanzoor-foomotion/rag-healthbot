
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

function getServerBaseUrl() {
  // Should point to the FastAPI base, including /api
  // Example: http://localhost:8000/api
  return process.env.RAG_HEALTHBOT_SERVER_URL ?? "http://localhost:8000/api";
}

type Context = { params: Promise<{ id: string }> };

export async function GET(req: NextRequest, context: Context) {
  try {
    const { id } = await context.params;
    const baseUrl = getServerBaseUrl();
    const upstream = await fetch(`${baseUrl}/conversations/${id}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error(e);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest, context: Context) {
  try {
    const { id } = await context.params;
    if (!id) {
      return NextResponse.json(
        { error: "Conversation ID is required" },
        { status: 400 }
      );
    }

    const baseUrl = getServerBaseUrl();
    const upstream = await fetch(`${baseUrl}/conversations/${id}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error(e);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}