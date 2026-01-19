import { connectDB } from "@/helpers/mongodb";
import Chat, { IConversation } from "@/schemas/Coversation";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
    try {
        await connectDB();

        const chats = await Chat.find().sort({ createdAt: -1 }); // latest first

        return NextResponse.json(chats);
    } catch (error) {
        console.error(error);
        return NextResponse.json({ error: 'Failed to fetch chats' }, { status: 500 });
    }
}

export async function POST(req: NextRequest) {
    try {
        await connectDB();

        const body = await req.json();
        const { title } = body;

        if (!title) {
            return NextResponse.json({ error: 'Title is required' }, { status: 400 });
        }

        const newChat: IConversation = new Chat({
            title,
            messages: [], // start with empty messages
        });

        const savedChat = await newChat.save();

        return NextResponse.json(savedChat, { status: 201 });
    } catch (err) {
        console.error('Error creating conversation:', err);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}



