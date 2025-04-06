import { createRequestHandler } from "@remix-run/express";
import express from "express";

// 引入构建文件
import * as build from "./build/index.js";

const app = express();
const PORT = process.env.PORT || 4000;

// 配置静态文件服务
app.use("/build", express.static("public/build"));
app.use(express.static("public"));

// 创建请求处理器
app.all(
    "*",
    createRequestHandler({
        build: build,
        mode: process.env.NODE_ENV,
    })
);

// 启动服务器
app.listen(PORT, () => {
    console.log(`Remix app is running at http://localhost:${PORT}`);
}); 