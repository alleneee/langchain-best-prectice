import { LoaderFunction } from "@remix-run/node";

// 一个空的favicon处理程序，防止404错误
export const loader: LoaderFunction = () => {
    // 返回一个1x1像素的透明PNG图像
    return new Response(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        {
            status: 200,
            headers: {
                "Content-Type": "image/png",
                "Cache-Control": "public, max-age=31536000",
            },
        }
    );
}; 