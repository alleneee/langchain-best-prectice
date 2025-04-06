import { ActionFunctionArgs, json } from "@remix-run/node";

export async function action({ request }: ActionFunctionArgs) {
    const requestBody = await request.json();

    // Proxy the request to the backend
    const response = await fetch("http://localhost:8000/api/document-qa/question/stream", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
    });

    // Create a new Response with the same headers and status
    return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    });
} 