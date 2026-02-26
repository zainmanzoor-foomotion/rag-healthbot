'use client';

import { useCallback, useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import ChatArea from '@/components/ChatArea';
import { Conversation, Message } from '@/types/types';
import { useSearchParams } from 'next/navigation';

type SseTokenEvent = { type: 'token'; token: string };

type ApiConversation = {
  _id?: string;
  id?: string;
  title: string;
  messages?: Array<{ userContent?: string; aiContent?: string }>;
  metadata?: Record<string, unknown>;
};

function getConversationId(chat: ApiConversation): string | null {
  const raw = chat._id ?? chat.id;
  if (raw == null) return null;
  const id = String(raw).trim();
  return id ? id : null;
}

function isSseTokenEvent(value: unknown): value is SseTokenEvent {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  return v.type === 'token' && typeof v.token === 'string';
}

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string>('');
  const [isSending, setIsSending] = useState(false);
  const [conversationLoading, setConversationLoading] = useState(false);

  const searchParams = useSearchParams();

  const fetchChats = useCallback(async () => {
    try {
      setConversationLoading(true)
      const res = await fetch('/api/conversations');

      const json = (await res.json()) as unknown;
      if (!Array.isArray(json)) {
        console.error('Unexpected /api/conversations payload:', json);
        setConversations([]);
        setCurrentChatId('');
        return;
      }

      const data = json as ApiConversation[];
      const formatted: Conversation[] = data
        .map((chat) => {
          const id = getConversationId(chat);
          if (!id) return null;
          return {
            id,
            title: chat.title,
            messages: (chat.messages || []).map((msg) => ({
              userContent: msg.userContent || '',
              aiContent: msg.aiContent || '',
            })),
          };
        })
        .filter((c): c is Conversation => Boolean(c));

      setConversations(formatted);

      const queryId = searchParams.get('id');
      if (queryId && formatted.some((c) => c.id === queryId)) {
        setCurrentChatId(queryId);
      } else if (formatted.length > 0) {
        setCurrentChatId(formatted[0].id);
      } else {
        setCurrentChatId('');
      }
    } catch (err) {
      console.error('Failed to fetch chats:', err);
    }
    finally {
      setConversationLoading(false)
    }
  }, [searchParams]);

  const streamChat = async (conversationId: string, message: string) => {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversationId, message }),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(text || `Chat failed (${res.status})`);
    }
    if (!res.body) {
      throw new Error('No response body');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, '\n');

      let sepIndex: number;
      while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);

        const dataLine = rawEvent
          .split('\n')
          .find((l) => l.startsWith('data: '));
        if (!dataLine) continue;

        const jsonPart = dataLine.slice('data: '.length);
        let evt: unknown;
        try {
          evt = JSON.parse(jsonPart);
        } catch {
          continue;
        }

        if (isSseTokenEvent(evt)) {
          const token = evt.token;
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id !== conversationId) return c;
              const messages = [...(c.messages || [])];
              if (!messages.length) return c;
              const lastIndex = messages.length - 1;
              const last = messages[lastIndex];
              messages[lastIndex] = {
                ...last,
                aiContent: (last.aiContent || '') + token,
              };
              return { ...c, messages };
            })
          );
        }
      }
    }
  };

  // Fetch conversations on mount
  useEffect(() => {
    fetchChats();
  }, [fetchChats]);

  const currentChat: Message[] =
    conversations.find((c) => c.id === currentChatId)?.messages ?? [];

  

  // Send message
  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    const chatIdToUse = currentChatId;
    if (!chatIdToUse) return;

    const userMessage: Message = { userContent: text, aiContent: '' };
    const assistantMessage: Message = { userContent: '', aiContent: '', loading: true };

    setConversations((prev) =>
      prev.map((c) =>
        c.id === chatIdToUse
          ? { ...c, messages: [...c.messages, userMessage, assistantMessage] }
          : c
      )
    );

    setIsSending(true);
    try {
      await streamChat(chatIdToUse, text);
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== chatIdToUse) return c;
          const messages = [...(c.messages || [])];
          if (!messages.length) return c;
          const lastIndex = messages.length - 1;
          messages[lastIndex] = { ...messages[lastIndex], loading: false };
          return { ...c, messages };
        })
      );
    } catch (e) {
      console.error(e);
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== chatIdToUse) return c;
          const messages = [...(c.messages || [])];
          if (!messages.length) return c;
          const lastIndex = messages.length - 1;
          messages[lastIndex] = {
            ...messages[lastIndex],
            loading: false,
            aiContent:
              (messages[lastIndex].aiContent || '') +
              '\n\n[Error] Failed to get response.',
          };
          return { ...c, messages };
        })
      );
    } finally {
      setIsSending(false);
    }
  };

  const startNewChat = async () => {
    const newTitle = `Chat ${conversations.length > 0 ? conversations.length + 1 : 1}`;

    try {
      const res = await fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      });

      await res.json();

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
      <ChatArea currentChat={currentChat} onSendMessage={handleSendMessage} isSending={isSending} />
    </div>
  );
}
