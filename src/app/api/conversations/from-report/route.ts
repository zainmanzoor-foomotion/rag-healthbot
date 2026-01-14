import { NextResponse } from "next/server";
import {connectDB} from "@/helpers/mongodb";
import Report from "@/schemas/Report";
import Conversation from "@/schemas/Coversation";
import { chunkText, createEmbeddings, upsertToPinecone } from "@/helpers/embeddings";

export async function POST(req: Request) {
  try {
    const { reportId } = await req.json();
    if (!reportId) return NextResponse.json({ error: "reportId required" }, { status: 400 });

    const pineconeIndexBaseName = process.env.PINECONE_INDEX;
    if (!pineconeIndexBaseName || !pineconeIndexBaseName.trim()) {
      return NextResponse.json(
        { error: "Missing PINECONE_INDEX env var (Pinecone index name)." },
        { status: 500 }
      );
    }

    await connectDB();
    const reportDoc = await Report.findById(reportId);
    if (!reportDoc) return NextResponse.json({ error: "not found" }, { status: 404 });

    const text = (reportDoc as any).extractedText || "";
    if (!text || text.length < 20) {
      return NextResponse.json({ error: "no text available for embeddings" }, { status: 400 });
    }

    let pineconeIndexNameUsed: string | undefined;
    let embeddingDimUsed: number | undefined;

    const chunks = chunkText(text, 1000, 200);
    if (chunks.length) {
      const embeddings = await createEmbeddings(chunks);
      const embeddingDim = embeddings?.[0]?.length ?? 0;
      if (!embeddingDim) {
        return NextResponse.json(
          { error: "Failed to generate embeddings (no embedding dimension)." },
          { status: 500 }
        );
      }

      const pineconeIndexName = `${pineconeIndexBaseName}-${embeddingDim}`;
      pineconeIndexNameUsed = pineconeIndexName;
      embeddingDimUsed = embeddingDim;

      const vectors = chunks.map((c, i) => ({
        id: `${reportId}::${i}`,
        metadata: { reportId, filename: reportDoc.filename || "", chunkIndex: i, text: c },
        values: embeddings[i],
      }));
        console.log("Created embeddings:", embeddings.length);
      await upsertToPinecone(pineconeIndexName, String(reportId), vectors);
    }

    console.log("Passed embeddings to Pinecone for report:", reportId);
    const conv = await Conversation.create({
      title: `Chat — ${reportDoc.filename || "Report"}`,
      messages: [],
      metadata: {
        reportId,
        pineconeIndex: pineconeIndexNameUsed,
        embeddingDim: embeddingDimUsed,
      },
      createdAt: new Date(),
    });

    return NextResponse.json({ id: conv._id.toString() });
  } catch (e) {
    console.error(e);
    return NextResponse.json({ error: "server" }, { status: 500 });
  }
}
