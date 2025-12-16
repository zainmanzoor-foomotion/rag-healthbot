import React, { useState, useRef, useEffect } from 'react';
import { Message } from '@/types/types'; // import your centralized types
import MessageLoader from './MessageLoader';
import { UIMessage } from 'ai';

interface ChatAreaProps {
    currentChat: Message[]; // now an array of Message from Home.tsx
    onSendMessage: (text: string) => void;
    messages: UIMessage[],
    loading: boolean,
    status: string
}


const ChatArea: React.FC<ChatAreaProps> = ({ currentChat, onSendMessage, messages, status, loading }) => {
    const [inputText, setInputText] = useState('');

    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [currentChat]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (status === 'ready') {
            if (inputText.trim()) {
                onSendMessage(inputText);
                setInputText('');
            }
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
                {currentChat.length === 0 && messages.length === 0 ?
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
                                        <p>{message.aiContent}</p>
                                    </div>
                                </div>
                            )}



                        </div>
                    ))}
                {messages.map(message => (
                    <div key={message.id}>
                        {message.role === 'user' ?
                            message.parts.map((part, index) =>
                                part.type === 'text' && <div key={index} className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                                    <div className={message.role === 'user' ? "max-w-4xl p-3 rounded-lg shadow-md bg-blue-600 text-white" :
                                        "max-w-4xl p-3 rounded-lg shadow-md bg-gray-700 text-gray-100"
                                    }>

                                        <p>{part.text}</p>
                                    </div>
                                </div>
                            )
                            :
                            message.parts.map((part, index) =>
                                part.type === 'text' && <div key={index} className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                                    <div className={message.role === 'user' ? "max-w-4xl p-3 rounded-lg shadow-md bg-blue-600 text-white" :
                                        "max-w-4xl p-3 rounded-lg shadow-md bg-gray-700 text-gray-100"
                                    }>


                                        <p>{part.text}</p>
                                    </div>
                                </div>
                            )
                        }
                    </div>
                ))}
                {status === 'submitted' &&
                    <div className="flex justify-start">
                        <div className="max-w-4xl p-3 rounded-lg shadow-md bg-gray-700 text-gray-100">
                            <MessageLoader />
                        </div>
                    </div>
                }
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
                        disabled={!inputText.trim() || status !== 'ready'}
                        className={`ml-3 py-3 px-5 rounded-lg transition duration-150 ${inputText.trim() && status == 'ready'
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
