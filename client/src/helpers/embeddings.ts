import { Errors, Pinecone } from "@pinecone-database/pinecone";
import type { RecordMetadataValue } from "@pinecone-database/pinecone";

const OLLAMA_HOST = process.env.OLLAMA_HOST ?? "http://127.0.0.1:11434";
const OLLAMA_EMBED_MODEL = process.env.OLLAMA_EMBED_MODEL ?? "all-minilm";

export function chunkText(text: string, chunkSize = 1000, overlap = 200) {
  const chunks: string[] = [];
  let i = 0;
  while (i < text.length) {
    const end = Math.min(i + chunkSize, text.length);
    chunks.push(text.slice(i, end).trim());
    i += chunkSize - overlap;
  }
  return chunks.filter(Boolean);
}

export async function createEmbeddings(inputs: string[]) {
  if (!inputs.length) return [];

  try {
    const resp = await fetch(`${OLLAMA_HOST}/api/embed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: OLLAMA_EMBED_MODEL, input: inputs }),
    });

    if (resp.ok) {
      const data = (await resp.json()) as { embeddings?: number[][] };
      if (Array.isArray(data.embeddings) && data.embeddings.length === inputs.length) {
        return data.embeddings;
      }
    }
  } catch {

  }

  const results: number[][] = [];
  for (const prompt of inputs) {
    const resp = await fetch(`${OLLAMA_HOST}/api/embeddings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: OLLAMA_EMBED_MODEL, prompt }),
    });
    if (!resp.ok) {
      const body = await resp.text().catch(() => "");
      throw new Error(`Ollama embeddings failed (${resp.status}): ${body}`);
    }
    const data = (await resp.json()) as { embedding?: number[] };
    if (!Array.isArray(data.embedding)) {
      throw new Error("Ollama embeddings response missing 'embedding'");
    }
    results.push(data.embedding);
  }
  return results;
}

export type PineconeVectorMetadata = Record<string, RecordMetadataValue>;

export type PineconeVector = {
  id: string;
  metadata: PineconeVectorMetadata;
  values: number[];
};

type PineconeCloud = "aws" | "gcp" | "azure";

function errorName(err: unknown): string | undefined {
  if (typeof err === "object" && err !== null && "name" in err) {
    const name = (err as { name?: unknown }).name;
    return typeof name === "string" ? name : undefined;
  }
  return undefined;
}

function isPineconeNotFound(err: unknown): boolean {
  return err instanceof Errors.PineconeNotFoundError || errorName(err) === "PineconeNotFoundError";
}

export async function upsertToPinecone(indexName: string, namespace: string, vectors: PineconeVector[]) {
  if (!indexName || !indexName.trim()) {
    throw new Error("Missing Pinecone index name. Set PINECONE_INDEX in your environment.");
  }
  if (!namespace || !namespace.trim()) {
    throw new Error("Missing Pinecone namespace.");
  }
  if (!vectors.length) return;

  const client = new Pinecone({
    apiKey: process.env.PINECONE_API_KEY!,
  });

  const upsertOnce = async () => {
    const index = client.index(indexName).namespace(namespace);
    await index.upsert(vectors);
  };

  try {
    await upsertOnce();
  } catch (e: unknown) {
    // If the index doesn't exist yet, optionally auto-create it.
    if (!isPineconeNotFound(e)) throw e;

    const dimension = vectors[0]?.values?.length;
    if (!dimension || dimension <= 0) {
      throw new Error("Cannot infer embedding dimension to create Pinecone index.");
    }

    const cloud = process.env.PINECONE_CLOUD as PineconeCloud | undefined;
    const region = process.env.PINECONE_REGION;

    if (!cloud || !region || !["aws", "gcp", "azure"].includes(cloud)) {
      throw new Error(
        `Pinecone index '${indexName}' not found. Create it in Pinecone or set PINECONE_CLOUD and PINECONE_REGION so the app can auto-create it.`
      );
    }

    await client.createIndex({
      name: indexName,
      dimension,
      spec: { serverless: { cloud, region } },
      suppressConflicts: true,
      waitUntilReady: true,
    });

    await upsertOnce();
  }
}

export async function queryPinecone(indexName: string, namespace: string, vector: number[], topK = 5) {
  if (!indexName || !indexName.trim()) {
    throw new Error("Missing Pinecone index name. Set PINECONE_INDEX in your environment.");
  }
  if (!namespace || !namespace.trim()) {
    throw new Error("Missing Pinecone namespace.");
  }
  const client = new Pinecone({
    apiKey: process.env.PINECONE_API_KEY!,
  });
  const index = client.index(indexName).namespace(namespace);
  try {
    const resp = await index.query({ vector, topK, includeMetadata: true });
    return resp.matches || [];
  } catch (e: unknown) {
    if (isPineconeNotFound(e)) {
      throw new Error(`Pinecone index '${indexName}' not found. Check PINECONE_INDEX or create the index in Pinecone.`);
    }
    throw e;
  }
}
