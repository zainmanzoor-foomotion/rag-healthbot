'use client';

import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import ChatArea from '@/components/ChatArea';
import { Conversation, Message } from '@/types/types';
import { IConversation } from '@/schemas/Coversation';
import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string>('');
  const [currentChat, setCurrentChat] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationLoading, setConversationLoading] = useState(false);

  const { messages, sendMessage, status } = useChat({
    id: currentChatId,
    transport: new DefaultChatTransport({
      api: '/api/chat',
    }),
  });


  // Fetch conversations on mount
  useEffect(() => {
    fetchChats();
  }, []);

  const fetchChats = async () => {
    try {
      setConversationLoading(true)
      const res = await fetch('/api/conversations');
      const data: IConversation[] = await res.json();

      const formatted: Conversation[] = data.map(chat => ({
        id: chat._id.toString(),
        title: chat.title,
        messages: (chat.messages || []).map(msg => ({
          userContent: msg.userContent || '',
          aiContent: msg.aiContent || '',
        })),
      }));

      setConversations(formatted);

      if (formatted.length > 0) {
        setCurrentChatId(formatted[0].id);
        setCurrentChat(formatted[0].messages);
      }
    } catch (err) {
      console.error('Failed to fetch chats:', err);
    }
    finally {
      setConversationLoading(false)
    }
  };

  // Update currentChat whenever currentChatId changes
  useEffect(() => {
    const chat = conversations.find(c => c.id === currentChatId);
    setCurrentChat(chat ? chat.messages : []);
  }, [currentChatId, conversations]);

  // Send message
  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;
    setLoading(true)
    if (text.trim()) {
      await sendMessage({ text });
      setLoading(false)
    }

    // let chatIdToUse = currentChatId;

    // const userMessage: Message = { userContent: text, aiContent: '' };
    // const loaderMessage: Message = { userContent: '', aiContent: '', loading: true };

    // // 2️⃣ Optimistic frontend update
    // setConversations(prev =>
    //   prev.map(c =>
    //     c.id === chatIdToUse
    //       ? { ...c, messages: [...c.messages, userMessage, loaderMessage] }
    //       : c
    //   )
    // );
    // setLoading(true)
    // // 3️⃣ Send to backend
    // const res = await fetch('/api/chat', {
    //   method: 'POST',
    //   body: JSON.stringify({ chatId: chatIdToUse, messages: userMessage }),
    //   headers: { 'Content-Type': 'application/json' },
    // });

    // if (!res.ok) {
    //   console.error('Error sending message');
    //   return;
    // }

    // // Get the updated chat with AI content from backend
    // const updatedChat = await res.json();

    // console.log('updated Chat', updatedChat)

    // setLoading(false)

    // // Update conversations state
    // setConversations(prev =>
    //   prev.map(c =>
    //     c.id === chatIdToUse
    //       ? {
    //         ...updatedChat,   // all other fields from backend
    //         id: updatedChat._id  // set id for frontend consistency
    //       }
    //       : c
    //   )
    // );
    // // Mark loader as complete (if you still have a loading flag in messages)
    // setConversations(prev =>
    //   prev.map(c => {
    //     if (c.id === chatIdToUse) {
    //       const updatedMessages = c.messages.map(m =>
    //         m.loading ? { ...m, loading: false } : m
    //       );
    //       return { ...c, messages: updatedMessages };
    //     }
    //     return c;
    //   })
    // );
  };

  const startNewChat = async () => {
    const newTitle = `Chat ${conversations.length > 0 ? conversations.length + 1 : 1}`;

    try {
      const res = await fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      });

      const data = await res.json();

      if (res.ok) {
        await fetchChats();
      }

    } catch (err) {
      console.error("Error creating chat:", err);
    }
  };
  const handleDeleteConversation = async (id: string) => {
    if (!confirm('Are you sure you want to delete this conversation?')) return;

    try {
      const res = await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
      const data = await res.json();

      if (res.ok) {
        await fetchChats();
      } else {
        console.error('Failed to delete conversation:', data.error);
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100 antialiased">
      <Sidebar
        conversations={conversations}
        currentChatId={currentChatId}
        setCurrentChatId={setCurrentChatId}
        startNewChat={startNewChat}
        onDeleteConversation={handleDeleteConversation}
        conversationLoading={conversationLoading}
      />
      <ChatArea currentChat={currentChat} onSendMessage={handleSendMessage} loading={loading}
        messages={messages} status={status} />
      {/* <div>
        Messgaes 
         {messages.map(message => (
        <div key={message.id}>d
          {message.role === 'user' ? 'User: ' : 'AI: '}
          {message.parts.map((part, index) =>
            part.type === 'text' ? <span key={index}>{part.text}</span> : null,
          )}
        </div>
      ))}
      </div> */}
    </div>
  );
}
