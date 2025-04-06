import { LoaderFunctionArgs, json } from "@remix-run/node";

export async function loader({ request }: LoaderFunctionArgs) {
    // Proxy the request to the backend
    const response = await fetch("http://localhost:8000/api/status", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    });

    const data = await response.json();

    return json(data, {
        status: response.status,
    });
} 