# 文档问答系统

基于LangChain 0.3和FastAPI实现的文档问答系统，采用RAG（检索增强生成）技术，支持多种文档格式和会话管理。

## 项目特点

- **多格式文档支持**: PDF、DOCX、TXT、CSV、XLSX等
- **向量检索**: 使用Milvus向量数据库实现高效语义搜索
- **会话管理**: 支持持久化会话历史，多轮对话
- **多种界面**:
  - Remix + Tailwind CSS前端 (美观现代的Web界面)
  - FastAPI Web接口 + 静态HTML前端
  - 命令行界面
  - Gradio界面(可选)
- **安全功能**: 验证码保护文档上传功能
- **灵活配置**: 通过环境变量和配置文件自定义系统行为

## 项目结构

```
.
├── app/               # FastAPI后端应用
│   ├── api/           # API接口实现
│   ├── core/          # 核心配置
│   ├── schemas/       # 数据模型
│   ├── services/      # 服务层
│   └── utils/         # 工具函数
├── web/              # Remix前端应用
├── data/              # 示例数据
├── vector_stores/     # 向量存储文件
├── uploads/           # 用户上传的文件
├── sessions/          # 会话数据
└── static/            # 静态文件
```

## 安装与配置

### 前置条件

- Python 3.9+
- Node.js 18+ (用于Remix前端)
- Milvus 数据库 (2.0+)

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/your-username/document-qa.git
cd document-qa
```

2. 创建Python虚拟环境并安装后端依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

3. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

4. 配置环境变量

```bash
cp template.env .env
# 编辑.env文件填写您的API密钥和配置
```

## 运行

使用启动脚本提供多种不同的运行模式:

```bash
# 全栈应用(Remix前端 + FastAPI后端)
./start-app.sh

# 仅API服务
./start.sh api

# 命令行界面
./start.sh cli

# Gradio界面 (可选)
./start.sh gradio
```

### 自定义端口

```bash
./start.sh api --port 9000
./start.sh gradio -p 8080
```

## 前端界面

### Remix Tailwind CSS前端

现代化的Web应用界面，访问 <http://localhost:3000>

特点:

- 美观直观的用户界面
- 实时对话体验
- 文档上传和会话管理
- 模型参数配置
- 文档来源显示

### 简易HTML前端

基础的Web界面，访问 <http://localhost:8000/static/index.html>

## API使用

系统提供以下主要API端点:

- `/api/document-qa/upload` - 上传并处理文档
- `/api/document-qa/question` - 提交问题并获取回答
- `/api/document-qa/captcha` - 获取验证码
- `/api/document-qa/status` - 检查系统状态
- `/api/document-qa/session` - 管理会话

完整API文档可通过 `/api/docs` 访问。

## 命令行界面

命令行界面支持以下命令:

- `/help` - 显示帮助信息
- `/load [路径]` - 加载文档
- `/status` - 查看系统状态
- `/new` - 创建新会话
- `/clear` - 清空当前会话
- `/model [模型名]` - 设置使用的模型
- `/temp [值]` - 设置温度参数 (0.0-1.0)
- `/exit` - 退出程序

## 文档

- [LangChain文档](https://python.langchain.com/docs)
- [FastAPI文档](https://fastapi.tiangolo.com)
- [Milvus文档](https://milvus.io/docs)
- [Remix文档](https://remix.run/docs)
- [Tailwind CSS文档](https://tailwindcss.com/docs)

## 许可证

MIT

## 贡献

欢迎通过Issue和Pull Request贡献代码！

## 前端开发

进入前端目录并运行开发服务器：

```bash
cd web
npm install
npm run dev
```

前端应用将在 <http://localhost:3000> 上运行。
