import {
    Links,
    LiveReload,
    Meta,
    Outlet,
    Scripts,
    ScrollRestoration,
} from "@remix-run/react";
import { LinksFunction } from "@remix-run/node";
import stylesUrl from "./tailwind.css?url";

export const links: LinksFunction = () => [
    { rel: "stylesheet", href: stylesUrl },
    { rel: "stylesheet", href: "/styles.css" },
    { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
];

export default function App() {
    return (
        <html lang="zh-CN">
            <head>
                <meta charSet="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <Meta />
                <Links />
            </head>
            <body className="min-h-screen bg-gray-50">
                <Outlet />
                <ScrollRestoration />
                <Scripts />
                <LiveReload />
            </body>
        </html>
    );
} 