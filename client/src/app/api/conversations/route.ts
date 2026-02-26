import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

function getServerBaseUrl() {
    // Should point to the FastAPI base, including /api
    // Example: http://localhost:8000/api
    return process.env.RAG_HEALTHBOT_SERVER_URL ?? "http://localhost:8000/api";
}

export async function GET() {
    try {
        const baseUrl = getServerBaseUrl();
        const upstream = await fetch(`${baseUrl}/conversations`, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
            cache: "no-store",
        });

        const text = await upstream.text();
        return new NextResponse(text, {
            status: upstream.status,
            headers: { "Content-Type": "application/json" },
        });
    } catch (error) {
        console.error(error);
        return NextResponse.json({ error: "Failed to fetch chats" }, { status: 500 });
    }
}

export async function POST(req: NextRequest) {
    try {
        const baseUrl = getServerBaseUrl();
        const body = await req.json();

        const upstream = await fetch(`${baseUrl}/conversations`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        const text = await upstream.text();
        return new NextResponse(text, {
            status: upstream.status,
            headers: { "Content-Type": "application/json" },
        });
    } catch (err) {
        console.error("Error creating conversation:", err);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}



