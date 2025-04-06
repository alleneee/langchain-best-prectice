import { useState, useRef, useEffect } from "react";
import { type MetaFunction } from "@remix-run/node";
import {
    ChatMessage,
    Source,
    createSession,
    sendStreamQuestion
} from "~/services/api";
import ReactMarkdown from 'react-markdown';

// 自定义ReactMarkdown组件以支持类名
const MarkdownRenderer = ({ children }: { children: string }) => {
    return (
        <div className="markdown">
            <ReactMarkdown>{children}</ReactMarkdown>
        </div>
    );
};

export const meta: MetaFunction = () => {
    return [
        { title: "旅游导游助手" },
        { name: "description", content: "您的专业旅游导游助手" },
    ];
};

export default function Index() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [question, setQuestion] = useState("");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [webSources, setWebSources] = useState<Source[]>([]);
    const inputRef = useRef<HTMLInputElement>(null);

    // 流式回答相关状态
    const [streamedContent, setStreamedContent] = useState("");
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamingWebSources, setStreamingWebSources] = useState<Source[]>([]);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom of messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, streamedContent]);

    // Initialize session
    useEffect(() => {
        const fetchSessionId = async () => {
            try {
                console.log("Attempting to create initial session...");
                const response = await createSession();
                setSessionId(response.session_id);
                console.log("Initial session created:", response.session_id);
            } catch (error) {
                console.error("Failed to initialize session:", error);
                // Optional: Add a user-facing error message here if initialization fails
            }
        };

        fetchSessionId();
    }, []);

    // 自动滚动到最新消息
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, streamedContent]);

    // 处理提交
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const inputValue = inputRef.current?.value || "";
        console.log("Form submitted with value:", inputValue);

        // 检查输入内容
        if (!inputValue.trim()) {
            console.warn("Input is empty, submission prevented.");
            return;
        }

        // 检查加载状态
        if (isLoading || isStreaming) {
            console.warn("Already loading or streaming, submission prevented.");
            return;
        }

        let currentSessionId = sessionId;

        // 检查会话ID，如果不存在则尝试创建
        if (!currentSessionId) {
            console.log("Session ID not found, attempting to create a new one...");
            try {
                const response = await createSession();
                currentSessionId = response.session_id;
                setSessionId(currentSessionId); // 更新状态
                console.log("New session created successfully:", currentSessionId);
            } catch (error) {
                console.error("Failed to create session during submit:", error);
                // Display error in chat
                setMessages(prev => [...prev, {
                    role: "assistant",
                    content: `抱歉，创建会话时遇到问题，请稍后重试。错误: ${error instanceof Error ? error.message : String(error)}`
                }]);
                return; // Stop execution
            }
        }

        // 再次确认会话ID是否有效
        if (!currentSessionId) {
            console.error("Session ID is still invalid after attempting creation. Aborting submit.");
            setMessages(prev => [...prev, {
                role: "assistant",
                content: "抱歉，无法获取有效的会话ID，请刷新页面重试。"
            }]);
            return;
        }

        try {
            setIsStreaming(true);
            setStreamedContent("");
            setMessages(prev => [...prev, { role: "user", content: inputValue }]);

            const currentQuestion = inputValue;
            if (inputRef.current) {
                inputRef.current.value = '';
            }
            setQuestion('');

            console.log(`Sending request for question: "${currentQuestion}" with session ID: ${currentSessionId}`);

            const response = await sendStreamQuestion(
                currentQuestion,
                currentSessionId,
                "gpt-4o",
                0.7,
                false
            );

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) {
                throw new Error("无法创建响应流读取器");
            }

            let completeText = '';
            let historyId = currentSessionId;
            let finalSources: Source[] = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value);
                const events = text.split("\n\n").filter(Boolean);

                for (const event of events) {
                    if (event.startsWith("data: ")) {
                        try {
                            const jsonData = JSON.parse(event.slice(6));
                            if (jsonData.text) {
                                completeText += jsonData.text;
                                setStreamedContent(completeText);
                            }
                            if (jsonData.done) {
                                if (jsonData.web_sources) {
                                    finalSources = jsonData.web_sources;
                                }
                                if (jsonData.history_id) {
                                    historyId = jsonData.history_id;
                                    // Optionally update session ID if backend modifies it
                                    // setSessionId(historyId); 
                                }
                            }
                        } catch (error) {
                            console.error("解析SSE数据出错:", error, "Event:", event);
                        }
                    }
                }
            }

            setMessages(prev => [...prev, { role: "assistant", content: completeText }]);
            setWebSources(finalSources);
            setStreamedContent("");
            // Update session ID if it was changed by the backend during the stream
            if (historyId !== currentSessionId) {
                setSessionId(historyId);
                console.log("Session ID updated by backend to:", historyId);
            }

        } catch (error) {
            console.error('流式处理错误:', error);
            setMessages(prev => [...prev, {
                role: "assistant",
                content: `处理您的问题时出错: ${error instanceof Error ? error.message : String(error)}`
            }]);
            setStreamedContent("");
        } finally {
            setIsStreaming(false);
        }
    };

    const handleNewChat = async () => {
        setIsLoading(true); // Indicate loading while creating new session
        try {
            console.log("Creating new chat session...");
            const response = await createSession();
            setSessionId(response.session_id);
            setMessages([]);
            setWebSources([]);
            setStreamedContent(""); // Clear any partial streaming content
            if (inputRef.current) inputRef.current.value = ''; // Clear input
            setQuestion('');
            console.log("New chat session created:", response.session_id);
        } catch (error) {
            console.error("Failed to create new session:", error);
            setMessages(prev => [...prev, {
                role: "assistant",
                content: `创建新会话失败: ${error instanceof Error ? error.message : String(error)}`
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    // Helper function for icons (replace with actual icons if available)
    function getIcon(iconName: string) {
        switch (iconName) {
            case 'map-pin': return '📍';
            case 'calendar': return '📅';
            case 'shopping-cart': return '🛒';
            case 'eye': return '👁️';
            case 'truck': return '🚚';
            case 'sparkles': return '✨';
            default: return '❔';
        }
    }

    return (
        <div className="flex flex-col h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-blue-600 text-white p-4 shadow-md">
                <div className="container mx-auto flex justify-between items-center">
                    <h1 className="text-xl font-bold">旅游导游助手</h1>
                    <button
                        onClick={handleNewChat}
                        className="bg-white text-blue-600 px-4 py-2 rounded-full text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50"
                        disabled={isLoading || isStreaming} // Disable while loading/streaming
                    >
                        新会话
                    </button>
                </div>
            </header>

            {/* Main chat area */}
            <div className="flex-1 container mx-auto flex flex-col max-w-4xl px-4">
                {/* Chat messages */}
                <div className="flex-1 overflow-y-auto py-4">
                    {messages.length === 0 && !isStreaming ? (
                        // Restore and enhance the initial introductory screen
                        <div className="h-full flex flex-col items-center justify-center text-center text-gray-600 px-4">
                            <div className="max-w-3xl w-full animate-fadeIn">
                                <h2 className="text-2xl font-semibold text-gray-800 mb-6">
                                    您的专业旅游导游助手已准备就绪
                                </h2>
                                <p className="text-gray-500 mb-8">
                                    可以提供全球各地的旅游建议和信息。
                                </p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-left mb-8">
                                    {/* Feature Card Component (Example Structure) */}
                                    {[ /* Array of feature objects */
                                        { icon: 'map-pin', title: '景点推荐', description: '探索世界各地的知名景点和隐藏宝藏，获取最佳参观建议' },
                                        { icon: 'calendar', title: '行程规划', description: '定制适合您的完美旅行计划，包括时间安排和路线建议' },
                                        { icon: 'shopping-cart', title: '购物指南', description: '了解当地特色商品和最佳购物场所，找到完美的纪念品' },
                                        { icon: 'eye', title: '文化体验', description: '深入了解目的地的历史、传统和当地文化特色' },
                                        { icon: 'truck', title: '交通出行', description: '获取关于公共交通、出租车、自驾等各种交通方式的建议' },
                                        { icon: 'sparkles', title: '实用贴士', description: '旅行安全、天气信息、当地风俗习惯和实用建议' },
                                    ].map((feature, index) => (
                                        <div key={index} className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 hover:border-blue-400 hover:shadow-lg transition-all duration-300">
                                            <h3 className="font-semibold text-blue-700 mb-2 flex items-center">
                                                {/* Placeholder for a better icon solution if available */}
                                                <span className="mr-2 text-blue-500">{getIcon(feature.icon)}</span>
                                                {feature.title}
                                            </h3>
                                            <p className="text-sm text-gray-600">{feature.description}</p>
                                        </div>
                                    ))}
                                </div>
                                <div className="bg-blue-50 text-blue-800 p-4 rounded-lg text-sm flex items-center justify-center">
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-600 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                    </svg>
                                    <span>集成高德地图数据，可提供详细的位置、路线规划和周边推荐。<b>试试问我：</b> "推荐北京三日游"、"上海有哪些美食"</span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        messages.map((msg, index) => (
                            <div key={index} className={`flex mb-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`rounded-xl p-3 max-w-lg ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white border border-gray-200 text-gray-800'}`}>
                                    <MarkdownRenderer>{msg.content}</MarkdownRenderer>
                                    {/* Display sources for assistant messages if available */}
                                    {msg.role === 'assistant' && index === messages.length - 1 && webSources.length > 0 && (
                                        <div className="mt-2 pt-2 border-t border-gray-300">
                                            <p className="text-xs font-semibold mb-1">参考来源:</p>
                                            <ul className="list-disc list-inside text-xs">
                                                {webSources.map((source, idx) => (
                                                    <li key={idx}>
                                                        <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-700 hover:underline">
                                                            {source.title || source.url}
                                                        </a>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                    {/* Display streaming content */}
                    {isStreaming && streamedContent && (
                        <div className="flex mb-4 justify-start">
                            <div className="rounded-xl p-3 max-w-lg bg-white border border-gray-200 text-gray-800">
                                <MarkdownRenderer>{streamedContent}</MarkdownRenderer>
                                {/* Optional: Add a subtle streaming indicator */}
                                <div className="mt-1 h-1 w-3 bg-blue-500 animate-pulse rounded-full"></div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input area - Simplified */}
                <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-sm mb-4">
                    <form
                        className="flex gap-2"
                        onSubmit={handleSubmit}
                    >
                        <div className="relative flex-1">
                            <input
                                ref={inputRef}
                                type="text"
                                name="question"
                                className="w-full border border-blue-300 rounded-xl px-4 py-3 pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors disabled:bg-gray-100"
                                placeholder={isLoading || isStreaming ? "请稍候..." : "询问旅游相关问题..."}
                                disabled={isLoading || isStreaming}
                            />
                            {/* Simple clear button - only show if input has text and not loading */}
                            {inputRef.current?.value && !isLoading && !isStreaming && (
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (inputRef.current) {
                                            inputRef.current.value = "";
                                            inputRef.current.focus(); // Focus after clearing
                                        }
                                    }}
                                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    aria-label="Clear input"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                    </svg>
                                </button>
                            )}
                        </div>

                        <button
                            type="submit"
                            className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-4 py-3 flex items-center justify-center gap-2 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                            disabled={isLoading || isStreaming} // Disable button while loading/streaming
                        >
                            {isLoading || isStreaming ? (
                                <>
                                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    处理中...
                                </>
                            ) : (
                                <>
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                        <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                                    </svg>
                                    发送
                                </>
                            )}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
} 