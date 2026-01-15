// import { streamText } from "ai";

import { google } from "@ai-sdk/google";
import Chat from "@/schemas/Coversation";
import { connectDB } from "@/helpers/mongodb";
import { queryPinecone, createEmbeddings } from "@/helpers/embeddings";


import { convertToModelMessages, streamText, UIMessage } from 'ai';

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

type PineconeMatchWithText = {
    metadata?: {
        text?: unknown;
        [key: string]: unknown;
    };
};

export async function POST(req: Request) {
    await connectDB();
    const {
        messages,
        id: chatId,
    }: {
        messages: UIMessage[];
        id: string;
    } = await req.json();

    const lastUserMessage = messages
        .filter((m) => m.role === "user")
        .at(-1);

    const userContent =
        lastUserMessage?.parts
            ?.filter((p) => p.type === "text")
            .map((p) => p.text)
            .join(" ") ?? "";

    const conversationDoc = await Chat.findById(chatId);
    let ragMessages = messages;

    if (conversationDoc?.metadata?.reportId && userContent) {
        const qe = (await createEmbeddings([userContent]))[0];
        const embeddingDim = qe?.length ?? 0;
        const indexBase = process.env.PINECONE_INDEX ?? "";
        const pineconeIndexName =
            (conversationDoc.metadata.pineconeIndex as string | undefined) ??
            (indexBase && embeddingDim ? `${indexBase}-${embeddingDim}` : indexBase);

        if (!pineconeIndexName) {
            throw new Error("Missing Pinecone index name. Set PINECONE_INDEX in your environment.");
        }

        const matches = await queryPinecone(
            pineconeIndexName,
            String(conversationDoc.metadata.reportId),
            qe,
            5
        );
        const retrievedTexts = (matches as PineconeMatchWithText[])
            .map((m) => (typeof m.metadata?.text === "string" ? m.metadata.text : ""))
            .filter(Boolean);
        if (retrievedTexts.length) {
            ragMessages = [
                {
                    id: "system-rag-context",
                    role: "system",
                    parts: [
                        {
                            type: "text",
                            text: `Relevant excerpts from the report:\n\n${retrievedTexts.slice(0,5).join("\n\n---\n\n")}\n\nUse them to answer the user concisely and cite when you used report content. The answer should be in layman terms that even non-professional people can understand.`,
                        }
                    ]
                },
                ...messages
            ];
        }
    }

    // 2️⃣ Start streaming AI response
    const result = streamText({
        model: google("gemini-2.5-flash"),
        system:
            'You are a helpful medical-information assistant. Always respond in GitHub-Flavored Markdown. Use clear section headings (## / ###), short paragraphs, and bullet lists where helpful. Keep a professional, calm tone. Avoid unnecessary filler. If information is missing or uncertain, say what is unknown and what to ask a clinician.',
        messages: convertToModelMessages(ragMessages),
        async onFinish({ text }) {
            // 3️⃣ Full AI text is available here
            const aiContent = text;

            // 4️⃣ Update chat document where _id === chatId
            await Chat.findByIdAndUpdate(
                chatId,
                {
                    $push: {
                        messages: {
                            userContent,
                            aiContent,
                            createdAt: new Date(),
                        },
                    },
                },
                { new: true }
            );
        },
    });

    // 5️⃣ Return stream response to frontend
    return result.toUIMessageStreamResponse();
}

