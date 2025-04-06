import { useState, useRef, useEffect } from "react";
import { type MetaFunction } from "@remix-run/node";
import { Form, useNavigation, useSearchParams } from "@remix-run/react";
import {
    ChatMessage,
    Source,
    createSession,
    getSystemStatus
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
        { title: "RAG文档问答系统" },
        { name: "description", content: "基于LangChain和向量数据库的文档问答系统" },
    ];
};

export default function Index() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [question, setQuestion] = useState("");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [selectedModel, setSelectedModel] = useState("gpt-4o");
    const [temperature, setTemperature] = useState(0.7);
    const [useWebSearch, setUseWebSearch] = useState(true);
    const [chatMode, setChatMode] = useState("document_qa");
    const [sources, setSources] = useState<string[]>([]);
    const [webSources, setWebSources] = useState<Source[]>([]);
    const [systemStatus, setSystemStatus] = useState({
        status: "loading",
        vector_store_ready: false,
        web_search_enabled: false
    });

    // 新增流式回答相关状态
    const [streamedContent, setStreamedContent] = useState("");
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamingSources, setStreamingSources] = useState<string[]>([]);
    const [streamingWebSources, setStreamingWebSources] = useState<Source[]>([]);
    const [useStreamingResponse, setUseStreamingResponse] = useState(true);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const navigation = useNavigation();
    const [searchParams] = useSearchParams();

    // Show upload success alert
    const uploadSuccess = searchParams.get("upload") === "success";

    // Scroll to bottom of messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Get system status
    useEffect(() => {
        const fetchSystemStatus = async () => {
            try {
                const status = await getSystemStatus();
                setSystemStatus(status);
            } catch (error) {
                console.error("Failed to get system status:", error);
            }
        };

        fetchSystemStatus();
    }, []);

    // Initialize session
    useEffect(() => {
        const fetchSessionId = async () => {
            try {
                const response = await createSession();
                setSessionId(response.session_id);
            } catch (error) {
                console.error("Failed to initialize session:", error);
            }
        };

        fetchSessionId();
    }, []);

    // 当模型变更时，对GPT-4o自动启用网络搜索
    useEffect(() => {
        if (selectedModel === "gpt-4o") {
            setUseWebSearch(true);
        }
    }, [selectedModel]);

    // 自动滚动到最新消息
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, streamedContent]);

    // 处理使用流式API
    const handleStreamSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || isLoading || isStreaming) return;

        try {
            setIsStreaming(true);
            setStreamedContent("");
            setMessages(prev => [...prev, { role: "user", content: question }]);

            // 立即清空输入框
            const currentQuestion = question;
            setQuestion('');

            // 根据选择的模式决定使用哪个API端点
            const apiEndpoint = chatMode === 'tour_guide'
                ? '/api/tour-guide/stream'
                : '/api/document-qa/question/stream';

            // 创建事件源
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: currentQuestion,
                    history_id: sessionId,
                    model: selectedModel,
                    temperature,
                    use_web_search: useWebSearch
                }),
            });

            // 初始化读取器
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) {
                throw new Error("无法创建响应流读取器");
            }

            // 读取流数据
            let completeText = '';
            let historyId = sessionId;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                // 解码当前块
                const text = decoder.decode(value);

                // 处理SSE格式的数据
                const events = text.split("\n\n").filter(Boolean);

                for (const event of events) {
                    if (event.startsWith("data: ")) {
                        try {
                            const jsonData = JSON.parse(event.slice(6));
                            completeText += jsonData.text || '';
                            setStreamedContent(completeText);

                            if (jsonData.done) {
                                // 最后一个块包含源和会话ID信息
                                if (jsonData.sources) {
                                    setStreamingSources(jsonData.sources);
                                }
                                if (jsonData.web_sources) {
                                    setStreamingWebSources(jsonData.web_sources);
                                }
                                if (jsonData.history_id) {
                                    historyId = jsonData.history_id;
                                    setSessionId(historyId);
                                }
                            }
                        } catch (error) {
                            console.error("解析SSE数据出错:", error);
                        }
                    }
                }
            }

            // 流完成后，添加完整消息到历史
            setMessages(prev => [...prev, { role: "assistant", content: completeText }]);
            setSources(streamingSources);
            setWebSources(streamingWebSources);
            setStreamedContent("");
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

    const handleSubmit = async (e: React.FormEvent) => {
        // 如果启用了流式响应，则使用流式提交方法
        if (useStreamingResponse) {
            return handleStreamSubmit(e);
        }

        e.preventDefault();
        if (!question.trim() || isLoading) return;

        try {
            setIsLoading(true);
            setMessages(prev => [...prev, { role: "user", content: question }]);

            // 立即清空输入框
            const currentQuestion = question;
            setQuestion('');

            // 根据选择的模式决定使用哪个API端点
            const apiEndpoint = chatMode === 'tour_guide'
                ? '/api/tour-guide'
                : '/api/document-qa/question';

            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: currentQuestion,
                    history_id: sessionId,
                    model: selectedModel,
                    temperature,
                    use_web_search: useWebSearch
                }),
            });

            const data = await response.json();

            if (response.ok) {
                const { answer, sources = [], web_sources = [], history_id } = data;

                setMessages(prev => [...prev, { role: "assistant", content: answer }]);
                setSources(sources);
                setWebSources(web_sources);
                setSessionId(history_id);
            } else {
                throw new Error(data.detail || '请求失败');
            }
        } catch (error) {
            console.error('问题处理错误:', error);
            setMessages(prev => [...prev, {
                role: "assistant",
                content: `处理您的问题时出错: ${error instanceof Error ? error.message : String(error)}`
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleNewChat = async () => {
        try {
            const response = await createSession();
            setSessionId(response.session_id);
            setMessages([]);
            setSources([]);
            setWebSources([]);
        } catch (error) {
            console.error("Failed to create new session:", error);
        }
    };

    return (
        <div className="flex h-screen">
            {/* Sidebar */}
            <div className="w-64 bg-gray-800 text-white p-4 flex flex-col">
                <h1 className="text-xl font-bold mb-6">RAG文档问答系统</h1>

                <button
                    onClick={handleNewChat}
                    className="btn bg-primary-600 hover:bg-primary-700 text-white mb-4"
                >
                    新会话
                </button>

                <div className="space-y-6 flex-grow">
                    <div>
                        <h2 className="text-sm uppercase font-semibold text-gray-400 mb-2">系统状态</h2>
                        <div className="text-sm">
                            <div className="flex items-center mb-1">
                                <div className={`w-2 h-2 rounded-full mr-2 ${systemStatus.status === "ready" ? "bg-green-500" : "bg-red-500"}`}></div>
                                <span>系统: {systemStatus.status === "ready" ? "就绪" : "未就绪"}</span>
                            </div>
                            <div className="flex items-center mb-1">
                                <div className={`w-2 h-2 rounded-full mr-2 ${systemStatus.vector_store_ready ? "bg-green-500" : "bg-yellow-500"}`}></div>
                                <span>向量存储: {systemStatus.vector_store_ready ? "已加载" : "未加载"}</span>
                            </div>
                            <div className="flex items-center">
                                <div className={`w-2 h-2 rounded-full mr-2 ${systemStatus.web_search_enabled ? "bg-green-500" : "bg-gray-500"}`}></div>
                                <span>网络搜索: {systemStatus.web_search_enabled ? "可用" : "不可用"}</span>
                            </div>
                        </div>
                    </div>

                    <div>
                        <h2 className="text-sm uppercase font-semibold text-gray-400 mb-2">模型设置</h2>
                        <div className="space-y-2">
                            <div>
                                <label className="block text-sm mb-1">对话模式</label>
                                <select
                                    value={chatMode}
                                    onChange={(e) => setChatMode(e.target.value)}
                                    className="w-full bg-gray-700 rounded px-2 py-1 text-sm"
                                >
                                    <option value="document_qa">文档问答</option>
                                    <option value="tour_guide">旅游导游</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm mb-1">模型</label>
                                <select
                                    value={selectedModel}
                                    onChange={(e) => setSelectedModel(e.target.value)}
                                    className="w-full bg-gray-700 rounded px-2 py-1 text-sm"
                                >
                                    <option value="gpt-4o">GPT-4o</option>
                                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm mb-1">温度: {temperature}</label>
                                <input
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.1"
                                    value={temperature}
                                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                    className="w-full"
                                />
                            </div>

                            <div className="flex items-center">
                                <input
                                    type="checkbox"
                                    id="streamingResponse"
                                    checked={useStreamingResponse}
                                    onChange={(e) => setUseStreamingResponse(e.target.checked)}
                                    className="mr-2"
                                />
                                <label htmlFor="streamingResponse" className="text-sm">
                                    启用流式响应
                                </label>
                            </div>
                        </div>
                    </div>

                    <div>
                        <h2 className="text-sm uppercase font-semibold text-gray-400 mb-2">文档上传</h2>
                        <Form
                            action="/upload"
                            method="post"
                            encType="multipart/form-data"
                            className="space-y-2"
                        >
                            <input
                                type="file"
                                name="file"
                                className="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:text-sm file:bg-primary-600 file:text-white hover:file:bg-primary-700"
                            />
                            <input
                                type="text"
                                name="collection_name"
                                placeholder="集合名称"
                                defaultValue="document_collection"
                                className="w-full bg-gray-700 rounded px-2 py-1 text-sm"
                            />
                            <button
                                type="submit"
                                className="btn bg-gray-600 hover:bg-gray-700 text-white w-full text-sm"
                                disabled={navigation.state === "submitting"}
                            >
                                {navigation.state === "submitting" ? "上传中..." : "上传文档"}
                            </button>
                        </Form>
                    </div>
                </div>

                <div className="text-xs text-gray-500 mt-6">
                    <p>会话ID: {sessionId || "未初始化"}</p>
                    <p>版本: 1.0.0</p>
                </div>
            </div>

            {/* Main chat area */}
            <div className="flex-1 flex flex-col">
                {/* Chat messages */}
                <div className="flex-1 overflow-y-auto p-4 bg-white">
                    {uploadSuccess && (
                        <div className="mb-4 p-3 text-green-700 bg-green-100 rounded border border-green-200">
                            文档上传成功！现在您可以开始询问关于文档的问题。
                        </div>
                    )}

                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center text-gray-500">
                            <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                            <h2 className="text-xl font-semibold mb-2">开始一个新对话</h2>
                            <p className="max-w-md">
                                {chatMode === 'tour_guide' ?
                                    '您可以询问全球各地的旅游景点、行程安排、美食推荐等旅游相关问题，导游助手将为您提供专业建议。' :
                                    '您可以询问有关已上传文档的问题，或者开启网络搜索后进行通用问答。'
                                }
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {messages.map((message, index) => (
                                <div key={index} className={`flex items-start ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                                    {message.role === "assistant" && (
                                        <div className="flex-shrink-0 mr-3">
                                            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-teal-400 flex items-center justify-center text-white">
                                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                                                    <path d="M16.5 7.5h-9v9h9v-9z" />
                                                    <path fillRule="evenodd" d="M8.25 2.25A.75.75 0 019 3v.75h2.25V3a.75.75 0 011.5 0v.75H15V3a.75.75 0 011.5 0v.75h.75a3 3 0 013 3v.75H21A.75.75 0 0121 9h-.75v2.25H21a.75.75 0 010 1.5h-.75V15H21a.75.75 0 010 1.5h-.75v.75a3 3 0 01-3 3h-.75V21a.75.75 0 01-1.5 0v-.75h-2.25V21a.75.75 0 01-1.5 0v-.75H9V21a.75.75 0 01-1.5 0v-.75h-.75a3 3 0 01-3-3v-.75H3A.75.75 0 013 15h.75v-2.25H3a.75.75 0 010-1.5h.75V9H3a.75.75 0 010-1.5h.75v-.75a3 3 0 013-3h.75V3a.75.75 0 01.75-.75zM6 6.75A.75.75 0 016.75 6h10.5a.75.75 0 01.75.75v10.5a.75.75 0 01-.75.75H6.75a.75.75 0 01-.75-.75V6.75z" clipRule="evenodd" />
                                                </svg>
                                            </div>
                                        </div>
                                    )}
                                    <div
                                        className={`max-w-3xl rounded-2xl px-4 py-3 ${message.role === "user"
                                            ? "bg-primary-600 text-white"
                                            : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100"
                                            }`}
                                    >
                                        {message.role === "assistant" ? (
                                            <MarkdownRenderer>
                                                {message.content}
                                            </MarkdownRenderer>
                                        ) : (
                                            <p>{message.content}</p>
                                        )}
                                    </div>
                                    {message.role === "user" && (
                                        <div className="flex-shrink-0 ml-3">
                                            <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-gray-600">
                                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                                                    <path fillRule="evenodd" d="M7.5 6a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM3.751 20.105a8.25 8.25 0 0116.498 0 .75.75 0 01-.437.695A18.683 18.683 0 0112 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 01-.437-.695z" clipRule="evenodd" />
                                                </svg>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}

                            {/* 流式内容渲染 */}
                            {isStreaming && streamedContent && (
                                <div className="flex items-start justify-start">
                                    <div className="flex-shrink-0 mr-3">
                                        <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-teal-400 flex items-center justify-center text-white">
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                                                <path d="M16.5 7.5h-9v9h9v-9z" />
                                                <path fillRule="evenodd" d="M8.25 2.25A.75.75 0 019 3v.75h2.25V3a.75.75 0 011.5 0v.75H15V3a.75.75 0 011.5 0v.75h.75a3 3 0 013 3v.75H21A.75.75 0 0121 9h-.75v2.25H21a.75.75 0 010 1.5h-.75V15H21a.75.75 0 010 1.5h-.75v.75a3 3 0 01-3 3h-.75V21a.75.75 0 01-1.5 0v-.75h-2.25V21a.75.75 0 01-1.5 0v-.75H9V21a.75.75 0 01-1.5 0v-.75h-.75a3 3 0 01-3-3v-.75H3A.75.75 0 013 15h.75v-2.25H3a.75.75 0 010-1.5h.75V9H3a.75.75 0 010-1.5h.75v-.75a3 3 0 013-3h.75V3a.75.75 0 01.75-.75zM6 6.75A.75.75 0 016.75 6h10.5a.75.75 0 01.75.75v10.5a.75.75 0 01-.75.75H6.75a.75.75 0 01-.75-.75V6.75z" clipRule="evenodd" />
                                            </svg>
                                        </div>
                                    </div>
                                    <div className="max-w-3xl rounded-2xl px-4 py-3 bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100">
                                        <MarkdownRenderer>
                                            {streamedContent}
                                        </MarkdownRenderer>
                                        <div className="mt-2 flex">
                                            <div className="typing-indicator">
                                                <span></span>
                                                <span></span>
                                                <span></span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* Sources panel */}
                {(sources.length > 0 || webSources.length > 0) && (
                    <div className="bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 p-4 max-h-64 overflow-y-auto">
                        <h3 className="font-medium text-gray-700 dark:text-gray-300 mb-2">参考来源</h3>
                        <div className="space-y-2">
                            {sources.map((source, index) => (
                                <div key={`doc-${index}`} className="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
                                    <div className="font-medium flex items-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1 text-primary-500" viewBox="0 0 20 20" fill="currentColor">
                                            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
                                        </svg>
                                        文档
                                    </div>
                                    <div className="truncate mt-1 text-xs pl-5">{source}</div>
                                </div>
                            ))}
                            {webSources.map((source, index) => (
                                <div key={`web-${index}`} className="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
                                    <div className="font-medium flex items-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1 text-primary-500" viewBox="0 0 20 20" fill="currentColor">
                                            <path fillRule="evenodd" d="M4.083 9h1.946c.089-1.546.383-2.97.837-4.118A6.004 6.004 0 004.083 9zM10 2a8 8 0 100 16 8 8 0 000-16zm0 2c-.076 0-.232.032-.465.262-.238.234-.497.623-.737 1.182-.389.907-.673 2.142-.766 3.556h3.936c-.093-1.414-.377-2.649-.766-3.556-.24-.56-.5-.948-.737-1.182C10.232 4.032 10.076 4 10 4zm3.971 5c-.089-1.546-.383-2.97-.837-4.118A6.004 6.004 0 0115.917 9h-1.946zm-2.003 2H8.032c.093 1.414.377 2.649.766 3.556.24.56.5.948.737 1.182.233.23.389.262.465.262.076 0 .232-.032.465-.262.238-.234.498-.623.737-1.182.389-.907.673-2.142.766-3.556zm1.166 4.118c.454-1.147.748-2.572.837-4.118h1.946a6.004 6.004 0 01-2.783 4.118zm-6.268 0C6.412 13.97 6.118 12.546 6.03 11H4.083a6.004 6.004 0 002.783 4.118z" clipRule="evenodd" />
                                        </svg>
                                        <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">
                                            {source.title || "网页来源"}
                                        </a>
                                    </div>
                                    <div className="text-xs text-gray-500 dark:text-gray-400 truncate pl-5">{source.url}</div>
                                    <div className="text-xs mt-1 line-clamp-2 pl-5">{source.content}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Input area */}
                <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                    <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-2">
                        <div className="relative flex-1">
                            <input
                                type="text"
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
                                className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 rounded-xl px-4 py-3 pr-10 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-white"
                                placeholder={`${isLoading || isStreaming ? "请稍候..." : "输入您的问题..."}`}
                                disabled={isLoading || isStreaming}
                            />
                            {question.trim() && !isLoading && !isStreaming && (
                                <button
                                    type="button"
                                    onClick={() => setQuestion("")}
                                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                    </svg>
                                </button>
                            )}
                        </div>
                        <button
                            type="submit"
                            className="bg-primary-600 hover:bg-primary-700 text-white rounded-xl px-4 py-3 flex items-center justify-center gap-2 disabled:bg-gray-300 disabled:text-gray-500 transition-colors"
                            disabled={isLoading || isStreaming || !question.trim()}
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
                    <div className="text-xs text-gray-400 mt-2">
                        {chatMode === 'tour_guide'
                            ? '请输入旅游相关问题，例如景点推荐、行程安排等'
                            : '输入问题以获取答案，或上传文档后针对文档内容提问'}
                    </div>
                </div>
            </div>
        </div>
    );
} 