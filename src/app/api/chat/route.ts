import { streamText } from "ai";
import { google } from "@ai-sdk/google";
import Chat from "@/schemas/Coversation";
import { connectDB } from "@/helpers/mongodb";

export async function POST(req: Request) {
    try {
        await connectDB();

        const body = await req.json();
        const { chatId, messages } = body;

        const { userContent } = messages

        if (!chatId || !userContent) {
            return new Response(
                JSON.stringify({ error: "chatId or userContent required" }),
                { status: 400 }
            );
        }

        // ✅ Await the result!
        const result = await streamText({
            model: google("gemini-2.5-flash-lite"),
            messages: [{ role: "user", content: userContent }],
        });

        // Now you can safely access full AI text
        const aiContent = await result.text; // <-- await here

        // Save to DB
        const updatedChat = await Chat.findByIdAndUpdate(
            chatId,
            { $push: { messages: { userContent, aiContent } } },
            { new: true }
        );

        return new Response(JSON.stringify(updatedChat), { status: 200 });
    } catch (err) {
        console.error("Chat API Error:", err);
        return new Response(JSON.stringify({ error: "Internal Server Error" }), { status: 500 });
    }
}
