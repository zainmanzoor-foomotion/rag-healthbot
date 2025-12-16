import React, { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { Conversation } from '@/types/types';
import MessageLoader from './MessageLoader';

interface SidebarProps {
    conversations: Conversation[];
    currentChatId: string;
    setCurrentChatId: (id: string) => void;
    startNewChat: () => void;
    onDeleteConversation: (id: string) => void;
    conversationLoading: boolean
}

const Sidebar: React.FC<SidebarProps> = ({
    conversations,
    currentChatId,
    setCurrentChatId,
    startNewChat,
    onDeleteConversation,
    conversationLoading
}) => {
    const [hoveredChatId, setHoveredChatId] = useState<string | null>(null);

    return (
        <aside className="w-70 bg-gray-900 border-r border-gray-800 flex flex-col p-5 shadow-xl">
            <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-800">
                <span className="text-xl font-semibold text-white">Next.js Chat</span>
                <button
                    onClick={startNewChat}
                    className="text-gray-400 hover:text-white transition duration-150 p-1 rounded-md hover:bg-gray-800 border border-gray-700 hover:border-white"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                    </svg>
                </button>
            </div>

            <div className="flex-grow space-y-2 overflow-y-auto custom-scrollbar">

                {conversations.map((chat, index) => (
                    <div
                        key={chat.id || index}
                        onClick={() => setCurrentChatId(chat.id)}
                        onMouseEnter={() => setHoveredChatId(chat.id)}
                        onMouseLeave={() => setHoveredChatId(null)}
                        className={`history-item cursor-pointer p-2 rounded-lg text-sm transition duration-150 flex items-center justify-between 
            ${chat.id === currentChatId ? 'bg-gray-700 text-white font-medium' : 'hover:bg-gray-800 text-gray-300'}`}
                    >
                        <span className="flex-1 truncate pr-2">{chat.title}</span>
                        <button
                            onClick={e => {
                                e.stopPropagation();
                                onDeleteConversation(chat.id);
                            }}
                            className={`text-gray-400 hover:text-red-500 p-1 rounded-md transition-opacity duration-200
              ${chat.id === currentChatId || hoveredChatId === chat.id ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
                        >
                            <Trash2 className="h-4 w-4" />
                        </button>
                    </div>
                ))}
                {conversations.length === 0 && conversationLoading &&
                    <div className='flex items-center justify-center'>
                        <MessageLoader />
                    </div>}
            </div>
        </aside>
    );
};

export default Sidebar;
