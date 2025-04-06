import { json } from "@remix-run/node";

export function loader() {
    return json(
        {
            short_name: "RAG问答系统",
            name: "RAG文档问答系统",
            icons: [
                {
                    src: "/favicon.ico",
                    sizes: "64x64 32x32 24x24 16x16",
                    type: "image/x-icon"
                }
            ],
            start_url: ".",
            display: "standalone",
            theme_color: "#000000",
            background_color: "#ffffff"
        },
        {
            headers: {
                "Cache-Control": "public, max-age=86400",
                "Content-Type": "application/json"
            }
        }
    );
} 