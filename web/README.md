# RAG Document QA Frontend

基于Remix构建的RAG文档问答系统前端，为用户提供现代化的文档问答体验。

## 功能特点

- 基于Remix框架构建
- Tailwind CSS提供现代设计
- 集成Markdown渲染支持
- 流式响应支持
- 文档上传功能
- 多模型选择
- 参数调整
- 来源显示

## 快速开始

要启动前端应用，请运行：

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

应用将在 <http://localhost:3000> 上可访问。

## 开发

要进行开发：

1. 克隆仓库
2. 进入web目录
3. 安装依赖
4. 启动开发服务器

```bash
git clone https://github.com/yourusername/langchain-best-practice.git
cd web
npm install
npm run dev
```

## 构建

要构建生产版本：

```bash
npm run build
```

构建产物将在 `build/` 目录中生成。

## API集成

前端通过以下API与后端交互：

- `/api/document-qa/question` - 提交问题并获取回答
- `/api/document-qa/question/stream` - 流式问答
- `/api/document-qa/upload` - 上传文档
- `/api/tour-guide` - 旅游导游模式问答
- `/api/tour-guide/stream` - 旅游导游模式流式问答
- `/api/status` - 获取系统状态
- `/api/session` - 创建或获取会话

## 目录结构

```
web/
├── app/              # 应用代码
│   ├── routes/       # 路由定义
│   ├── services/     # API 服务
│   └── tailwind.css  # 样式文件
├── public/           # 静态资源
├── build/            # 构建产物
└── package.json      # 项目配置
```

## 环境变量

- `API_URL` - 设置API服务器URL（默认为本地）
