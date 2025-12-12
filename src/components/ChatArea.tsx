import React, { useState, useRef, useEffect } from 'react';
import { Message } from '@/types/types'; // import your centralized types

interface ChatAreaProps {
    currentChat: Message[]; // now an array of Message from Home.tsx
    onSendMessage: (text: string) => void;
}

// Loader for AI response
const MessageLoader: React.FC = () => (
    <div className="flex items-center space-x-1 p-2 bg-gray-800 rounded-lg max-w-xs animate-pulse">
        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
    </div>
);

const ChatArea: React.FC<ChatAreaProps> = ({ currentChat, onSendMessage }) => {
    const [inputText, setInputText] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [currentChat]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputText.trim()) {
            onSendMessage(inputText);
            setInputText('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e as unknown as React.FormEvent);
        }
    };

    return (
        <main className="flex-1 flex flex-col">
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-4">
                {currentChat.length === 0 ?
                    (<div className="flex h-full items-center justify-center text-gray-500 text-xl"> Start a new conversation
                    </div>) :
                    currentChat.map((message, index) => (
                        <div key={index} className="space-y-3">

                            {/* USER MESSAGE */}
                            {message.userContent && (
                                <div className="flex justify-end">
                                    <div className="max-w-4xl p-3 rounded-lg shadow-md bg-blue-600 text-white">
                                        <p>{message.userContent}</p>
                                    </div>
                                </div>
                            )}

                            {/* AI MESSAGE */}
                            {(message.loading || message.aiContent) && (
                                <div className="flex justify-start">
                                    <div className="max-w-4xl p-3 rounded-lg shadow-md bg-gray-700 text-gray-100">
                                        {message.loading ? (
                                            <MessageLoader />
                                        ) : (
                                            <p>{message.aiContent}</p>
                                        )}
                                    </div>
                                </div>
                            )}

                        </div>
                    ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-gray-900 border-t border-gray-800">
                <form onSubmit={handleSubmit} className="flex items-center max-w-5xl mx-auto">
                    <textarea
                        value={inputText}
                        onChange={e => setInputText(e.target.value)}
                        onKeyDown={handleKeyDown}
                        rows={1}
                        placeholder="Send a message..."
                        className="flex-grow resize-none bg-gray-800 text-gray-100 border border-gray-700 rounded-lg py-3 px-4 focus:outline-none focus:ring-2 focus:ring-blue-500 overflow-hidden"
                        style={{ maxHeight: '200px' }}
                    />
                    <button
                        type="submit"
                        disabled={!inputText.trim()}
                        className={`ml-3 py-3 px-5 rounded-lg transition duration-150 ${inputText.trim()
                            ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
                            : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                            }`}
                    >
                        Send
                    </button>
                </form>
            </div>
        </main>
    );
};

export default ChatArea;
