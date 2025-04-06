/**
 * API服务 - 与后端通信
 */

import { json } from '@remix-run/node';

// 修改API基础URL，使用绝对路径指向后端服务器
const API_BASE_URL = "http://localhost:8001/api";

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export interface Source {
    url: string;
    title: string;
    content: string;
}

export interface QuestionResponse {
    answer: string;
    sources: string[];
    history: { role: string; content: string }[];
    history_id: string;
    web_sources?: Source[];
    tools_used?: string[]; // 添加工具使用信息
}

export interface SessionResponse {
    session_id: string;
    message: string;
    created_at: string;
}

export interface SystemStatusResponse {
    status: string;
    vector_store_ready: boolean;
    document_count?: number;
    web_search_enabled: boolean;
}

/**
 * 创建新会话
 */
export async function createSession(): Promise<SessionResponse> {
    console.log("Creating new session...");
    try {
        const url = `${API_BASE_URL}/session`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                "Content-Type": "application/json",
            },
        });

        if (!response.ok) {
            const errorText = await response.text().catch(() => "Unable to retrieve error details");
            console.error(`Failed to create session: ${response.status} - ${errorText}`);
            throw new Error(`Failed to create session: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        console.log("Session created successfully:", data.session_id);
        return data;
    } catch (error) {
        console.error("Error during session creation request:", error);
        throw error; // Re-throw the error to be caught by the caller
    }
}

/**
 * 发送问题
 */
export async function sendQuestion(
    question: string,
    sessionId: string | null,
    model: string,
    temperature: number,
    useDocQA: boolean
): Promise<QuestionResponse> {
    // 根据模式选择不同的端点
    const endpoint = useDocQA ? "document-qa/question" : "tour-guide";

    const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            question,
            history_id: sessionId,
            model,
            temperature,
            use_web_search: useDocQA,
        }),
    });

    if (!response.ok) {
        throw new Error(`发送问题失败: ${response.status}`);
    }

    return await response.json();
}

/**
 * 发送流式问题请求
 */
export async function sendStreamQuestion(
    question: string,
    sessionId: string, // Non-nullable now, ensured by caller
    model: string,
    temperature: number,
    useDocQA: boolean
): Promise<Response> {
    const endpoint = useDocQA ? "document-qa/question/stream" : "tour-guide/stream";
    const url = `${API_BASE_URL}/${endpoint}`;

    console.log(`Sending stream request to: ${url} with session ID: ${sessionId}`);

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question,
                history_id: sessionId,
                model,
                temperature,
                use_web_search: useDocQA,
            }),
        });

        if (!response.ok) {
            const errorText = await response.text().catch(() => "无法获取错误详情");
            console.error(`API Error: ${response.status} - ${errorText}`);
            throw new Error(`发送流式问题失败: ${response.status} - ${errorText}`);
        }

        console.log(`Stream request successful: ${response.status}`);
        return response;
    } catch (error) {
        console.error("Fetch failed for stream request:", error);
        throw error; // Re-throw
    }
}

/**
 * 获取系统状态
 */
export async function getSystemStatus(): Promise<SystemStatusResponse> {
    const response = await fetch(`${API_BASE_URL}/status`);

    if (!response.ok) {
        throw new Error('获取系统状态失败');
    }

    return await response.json();
}

// 上传文档
export async function uploadDocument(formData: FormData) {
    const response = await fetch(`${API_BASE_URL}/document-qa/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        throw new Error('文档上传失败');
    }

    return await response.json();
} 