/**
 * LangChain 最佳实践 API - 前端功能
 */

// API 端点
const API_ENDPOINTS = {
    SESSIONS: '/api/v1/document-qa/sessions',
    QUESTION: '/api/v1/document-qa/question',
    QUESTION_STREAM: '/api/v1/document-qa/question/stream',
    UPLOAD: '/api/v1/document-qa/upload',
    HEALTH: '/health'
};

// 会话管理
class SessionManager {
    constructor() {
        this.sessionId = null;
        this.messageHistory = [];
    }

    /**
     * 创建新会话
     * @returns {Promise<string>} 新会话ID
     */
    async createSession() {
        try {
            // 获取会话列表，然后使用问答API创建一个新会话
            const response = await fetch(API_ENDPOINTS.QUESTION, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    question: '你好',
                    temperature: 0.7
                }),
                // 添加错误处理选项
                cache: 'no-cache',
                credentials: 'same-origin',
                mode: 'cors',
                redirect: 'follow',
                referrerPolicy: 'no-referrer'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            this.sessionId = data.history_id;
            this.messageHistory = data.history || [];

            return this.sessionId;
        } catch (error) {
            console.error('创建会话失败:', error);
            throw error;
        }
    }

    /**
     * 获取会话历史
     * @returns {Promise<Array>} 消息历史
     */
    async getSessionHistory() {
        if (!this.sessionId) {
            throw new Error('没有活动会话');
        }

        try {
            const response = await fetch(API_ENDPOINTS.SESSIONS, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                cache: 'no-cache',
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            return data.sessions;
        } catch (error) {
            console.error('获取会话历史失败:', error);
            throw error;
        }
    }

    /**
     * 发送问题到聊天AI
     * @param {string} question 问题文本
     * @param {boolean} useStreaming 是否使用流式响应
     * @returns {Promise<Object>} 回答结果
     */
    async sendQuestion(question, useStreaming = false) {
        try {
            const endpoint = useStreaming ? API_ENDPOINTS.QUESTION_STREAM : API_ENDPOINTS.QUESTION;
            const requestData = {
                question: question,
                history_id: this.sessionId,
                temperature: 0.7,
                use_web_search: false
            };

            if (useStreaming) {
                return this._sendStreamingQuestion(endpoint, requestData);
            } else {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(requestData),
                    cache: 'no-cache',
                    credentials: 'same-origin',
                    mode: 'cors'
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }

                const data = await response.json();
                this.sessionId = data.history_id;
                this.messageHistory = data.history || [];

                return data;
            }
        } catch (error) {
            console.error('发送问题失败:', error);
            throw error;
        }
    }

    /**
     * 发送流式问题并处理SSE响应
     * @param {string} endpoint API端点
     * @param {Object} requestData 请求数据
     * @returns {Promise<EventSource>} 事件源对象
     */
    _sendStreamingQuestion(endpoint, requestData) {
        return new Promise((resolve, reject) => {
            try {
                fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'text/event-stream'
                    },
                    body: JSON.stringify(requestData),
                    cache: 'no-cache',
                    credentials: 'same-origin',
                    mode: 'cors'
                })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }

                        const reader = response.body.getReader();
                        const decoder = new TextDecoder();

                        // 返回读取器以便调用者可以处理事件
                        resolve({
                            reader: reader,
                            decoder: decoder,
                            cancel: () => reader.cancel()
                        });
                    })
                    .catch(error => {
                        reject(error);
                    });
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 验证API健康状态
     * @returns {Promise<Object>} 健康检查结果
     */
    static async checkHealth() {
        try {
            const response = await fetch(API_ENDPOINTS.HEALTH, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                cache: 'no-cache'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('健康检查失败:', error);
            throw error;
        }
    }
}

// 导出会话管理器类
window.SessionManager = SessionManager; 