
import { NextRequest, NextResponse } from 'next/server';
import { connectDB } from '@/helpers/mongodb';
import Chat from '@/schemas/Coversation';

export async function DELETE(req: NextRequest, context: { params: Promise<{ id: string }> }) {
  await connectDB();
  const { id } = await context.params;

  if (!id) return NextResponse.json({ error: 'Conversation ID is required' }, { status: 400 });

  const deletedChat = await Chat.findByIdAndDelete(id);

  if (!deletedChat) return NextResponse.json({ error: 'Conversation not found' }, { status: 404 });

  return NextResponse.json({ message: 'Conversation deleted successfully', id });
}