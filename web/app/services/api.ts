/**
 * API服务 - 与后端通信
 */

import { json } from '@remix-run/node';

const API_BASE_URL = "http://localhost:8000/api";

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
    const response = await fetch('/api/session', {
        method: 'POST',
    });

    if (!response.ok) {
        throw new Error('创建会话失败');
    }

    return await response.json();
}

/**
 * 发送问题
 */
export async function sendQuestion(
    question: string,
    sessionId: string | null,
    model: string,
    temperature: number,
    useWebSearch: boolean
): Promise<QuestionResponse> {
    const response = await fetch(`${API_BASE_URL}/question`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            question,
            history_id: sessionId,
            model,
            temperature,
            use_web_search: useWebSearch,
        }),
    });

    if (!response.ok) {
        throw new Error(`发送问题失败: ${response.status}`);
    }

    return await response.json();
}

/**
 * 获取系统状态
 */
export async function getSystemStatus(): Promise<SystemStatusResponse> {
    const response = await fetch('/api/status');

    if (!response.ok) {
        throw new Error('获取系统状态失败');
    }

    return await response.json();
}

// 上传文档
export async function uploadDocument(formData: FormData) {
    const response = await fetch('/api/document-qa/upload', {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        throw new Error('文档上传失败');
    }

    return await response.json();
} 