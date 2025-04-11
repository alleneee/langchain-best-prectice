# 文档问答系统

基于LangChain 0.3和FastAPI实现的文档问答系统，采用RAG（检索增强生成）技术，支持多种文档格式和会话管理。

## 项目特点

- **多格式文档支持**: 支持PDF、DOCX、TXT、CSV、XLSX、PPTX、HTML等多种格式
- **智能问答**: 通过LLM(GPT-4o/GPT-3.5)提供准确的问答服务
- **网络搜索增强**: 支持通过Web搜索增强回答质量
- **会话管理**: 支持持久化会话历史，实现多轮对话
- **高德地图旅游助手**: 基于高德地图MCP的旅游指南功能，提供全球旅游建议
- **多种界面**:
  - 基于Remix + Tailwind CSS的现代化Web前端
  - FastAPI Web接口
  - 命令行交互界面
- **安全功能**: 验证码保护文档上传功能
- **灵活配置**: 通过环境变量和配置文件自定义系统行为
- **多种文档处理方式**: 支持单文件上传、批量上传、目录处理和网页抓取

## 项目结构

```
.
├── app/               # FastAPI后端应用
│   ├── api/           # API接口实现
│   ├── api.py         # 主API实现文件
│   ├── core/          # 核心配置
│   ├── schemas/       # 数据模型
│   ├── services/      # 服务层
│   └── utils/         # 工具函数
├── web/               # Remix前端应用
│   ├── app/           # 前端源代码
│   │   ├── routes/    # 路由组件
│   │   └── services/  # 前端服务
├── data/              # 示例数据
├── uploads/           # 用户上传的文件
├── sessions/          # 会话数据
└── static/            # 静态文件
```

## 安装与配置

### 前置条件

- Python 3.9+
- Node.js 18+ (用于Remix前端)
- OpenAI API密钥
- 高德地图API密钥 (用于旅游助手功能)

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/yourusername/document-qa.git
cd document-qa
```

2. 创建Python虚拟环境并安装后端依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

pip install -r requirements.txt
# 安装高德地图MCP适配器
pip install langchain-mcp-adapters
```

3. 安装前端依赖

```bash
cd web
npm install
cd ..
```

4. 配置环境变量

```bash
cp template.env .env
# 编辑.env文件填写您的API密钥和配置
# 设置OPENAI_API_KEY和AMAP_API_KEY
```

## 运行

使用以下命令启动应用:

```bash
# 全栈应用(Remix前端 + FastAPI后端)
python -m app.main
# 同时在另一个终端中运行
cd web && npm run dev

# 仅API服务
python -m app.main

# 命令行界面
python cli.py
```

## 主要功能

### 文档处理

- 单文件上传和处理
- 批量文件上传
- 从URL加载网页内容
- 处理本地目录中的所有文档

### 问答功能

- 基于LLM的智能问答
- Web搜索增强的回答
- 流式输出回答(打字机效果)
- 支持GPT-4o、GPT-3.5等多种模型

### 旅游助手

- 基于高德地图MCP的旅游指南
- 搜索景点、酒店、餐厅等兴趣点
- 规划最佳旅游路线
- 获取公交路线和时间信息
- 查询城市天气情况
- 提供周边兴趣点推荐

### 会话管理

- 创建和保存会话
- 查看历史会话列表
- 删除会话

## API端点

系统提供以下主要API端点:

- `/api/document-qa/upload` - 上传并处理文档
- `/api/document-qa/question` - 提交问题并获取回答
- `/api/document-qa/captcha` - 获取验证码
- `/api/document-qa/status` - 检查系统状态
- `/api/document-qa/session` - 管理会话
- `/api/tour-guide` - 旅游助手

完整API文档可通过 `/api/docs` 访问。

## 前端界面

### Remix Tailwind CSS前端

现代化的Web应用界面，访问 <http://localhost:3000>

特点:

- 美观直观的用户界面
- 实时对话体验
- 文档上传和会话管理
- 模型参数配置
- 文档和网络搜索来源显示
- 旅游助手界面

## 文档

- [LangChain文档](https://python.langchain.com/docs)
- [FastAPI文档](https://fastapi.tiangolo.com)
- [Remix文档](https://remix.run/docs)
- [Tailwind CSS文档](https://tailwindcss.com/docs)
- [高德地图开放平台](https://lbs.amap.com/)

## 许可证

MIT

## 贡献

欢迎通过Issue和Pull Request贡献代码！
