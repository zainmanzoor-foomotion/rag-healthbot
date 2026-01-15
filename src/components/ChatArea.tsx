import React, { useState, useRef, useEffect } from 'react';
import { Message } from '@/types/types'; // import your centralized types
import MessageLoader from './MessageLoader';
import { UIMessage } from 'ai';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function MarkdownText({ text }: { text: string }) {
    return (
        <div className="whitespace-pre-wrap wrap-break-word">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    h1: ({ children }) => <h1 className="text-xl font-semibold mt-2 mb-2">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg font-semibold mt-3 mb-2">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-1">{children}</h3>,
                    p: ({ children }) => <p className="leading-relaxed my-2">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>,
                    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                    em: ({ children }) => <em className="italic">{children}</em>,
                    a: ({ children, href }) => (
                        <a
                            href={href}
                            target="_blank"
                            rel="noreferrer"
                            className="underline underline-offset-2 text-blue-200 hover:text-blue-100"
                        >
                            {children}
                        </a>
                    ),
                    blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-gray-500 pl-3 my-2 italic text-gray-100/90">{children}</blockquote>
                    ),
                    hr: () => <hr className="border-gray-500/60 my-3" />,
                    code: ({ children, className }) =>
                        className ? (
                            <code className={"font-mono text-sm " + className}>{children}</code>
                        ) : (
                            <code className="px-1 py-0.5 rounded bg-black/30 font-mono text-sm">{children}</code>
                        ),
                    pre: ({ children }) => (
                        <pre className="p-3 rounded bg-black/30 overflow-x-auto text-sm leading-relaxed">{children}</pre>
                    ),
                    table: ({ children }) => (
                        <div className="my-3 overflow-x-auto">
                            <table className="w-full text-sm border-collapse">{children}</table>
                        </div>
                    ),
                    th: ({ children }) => <th className="border border-gray-500/60 px-2 py-1 text-left">{children}</th>,
                    td: ({ children }) => <td className="border border-gray-500/60 px-2 py-1 align-top">{children}</td>,
                }}
            >
                {text}
            </ReactMarkdown>
        </div>
    );
}

interface ChatAreaProps {
    currentChat: Message[]; // now an array of Message from Home.tsx
    onSendMessage: (text: string) => void;
    messages: UIMessage[],
    status: string
}


const ChatArea: React.FC<ChatAreaProps> = ({ currentChat, onSendMessage, messages, status }) => {
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
                                        <MarkdownText text={message.userContent} />
                                    </div>
                                </div>
                            )}

                            {/* AI MESSAGE */}
                            {(message.loading || message.aiContent) && (
                                <div className="flex justify-start">
                                    <div className="max-w-4xl p-3 rounded-lg shadow-md bg-gray-700 text-gray-100">
                                        <MarkdownText text={message.aiContent} />
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

                                        <MarkdownText text={part.text} />
                                    </div>
                                </div>
                            )
                            :
                            message.parts.map((part, index) =>
                                part.type === 'text' && <div key={index} className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                                    <div className={message.role === 'user' ? "max-w-4xl p-3 rounded-lg shadow-md bg-blue-600 text-white" :
                                        "max-w-4xl p-3 rounded-lg shadow-md bg-gray-700 text-gray-100"
                                    }>


                                        <MarkdownText text={part.text} />
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
                        className="grow resize-none bg-gray-800 text-gray-100 border border-gray-700 rounded-lg py-3 px-4 focus:outline-none focus:ring-2 focus:ring-blue-500 overflow-hidden"
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
