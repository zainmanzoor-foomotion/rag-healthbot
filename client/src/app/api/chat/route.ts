export const runtime = "nodejs";

function getServerBaseUrl() {
    // Should point to the FastAPI base, including /api
    // Example: http://localhost:8000/api
    return process.env.RAG_HEALTHBOT_SERVER_URL ?? "http://localhost:8000/api";
}

export async function POST(req: Request) {
  const baseUrl = getServerBaseUrl();
  const body = await req.json();

  const upstream = await fetch(`${baseUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok) {
    const text = await upstream.text().catch(() => "");
    return new Response(text || "Upstream error", {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}

