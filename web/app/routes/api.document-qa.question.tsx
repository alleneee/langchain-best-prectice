import { ActionFunctionArgs, json } from "@remix-run/node";

export async function action({ request }: ActionFunctionArgs) {
    const requestBody = await request.json();

    // Proxy the request to the backend
    const response = await fetch("http://localhost:8000/api/document-qa/question", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
    });

    const data = await response.json();

    return json(data, {
        status: response.status,
    });
} 