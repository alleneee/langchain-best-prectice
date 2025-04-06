import { ActionFunctionArgs, json } from "@remix-run/node";

export async function action({ request }: ActionFunctionArgs) {
    // Proxy the request to the backend
    const response = await fetch("http://localhost:8000/api/session", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
    });

    const data = await response.json();

    return json(data, {
        status: response.status,
    });
} 