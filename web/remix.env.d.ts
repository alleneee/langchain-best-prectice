/// <reference types="@remix-run/dev" />
/// <reference types="@remix-run/node" />
/// <reference types="@remix-run/react" />
/// <reference types="vite/client" />

interface Window {
    ENV: {
        API_URL: string;
    };
}

declare global {
    namespace NodeJS {
        interface ProcessEnv {
            VITE_API_URL?: string;
        }
    }
} 