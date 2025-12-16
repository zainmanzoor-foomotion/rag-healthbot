// import { streamText } from "ai";
import { google } from "@ai-sdk/google";
import Chat from "@/schemas/Coversation";
import { connectDB } from "@/helpers/mongodb";


import { convertToModelMessages, streamText, UIMessage } from 'ai';

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

export async function POST(req: Request) {
    await connectDB()
    const {
        messages,
        id: chatId,
    }: {
        messages: UIMessage[];
        id: string;
    } = await req.json();

    // 1️⃣ Get last user message
    const lastUserMessage = messages
        .filter((m) => m.role === "user")
        .at(-1);

    const userContent =
        lastUserMessage?.parts
            ?.filter((p) => p.type === "text")
            .map((p) => p.text)
            .join(" ") ?? "";

    // 2️⃣ Start streaming AI response
    const result = streamText({
        model: google("gemini-2.5-flash"),
        system: "You are a helpful assistant.",
        messages: convertToModelMessages(messages),
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

