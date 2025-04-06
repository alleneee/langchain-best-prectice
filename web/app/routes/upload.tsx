import { useState } from "react";
import { json, redirect, ActionFunction } from "@remix-run/node";
import { useActionData, Form } from "@remix-run/react";

export const action: ActionFunction = async ({ request }) => {
    try {
        const formData = await request.formData();
        const file = formData.get("file") as File;
        const collectionName = formData.get("collection_name") as string || "document_collection";

        if (!file || file.size === 0) {
            return json({ error: "请选择要上传的文件" }, { status: 400 });
        }

        // Create a new FormData object to send to the API
        const apiFormData = new FormData();
        apiFormData.append("file", file);
        apiFormData.append("collection_name", collectionName);

        // Send to the API
        const response = await fetch("http://localhost:8000/api/upload", {
            method: "POST",
            body: apiFormData,
        });

        const result = await response.json();

        if (!response.ok) {
            return json({ error: result.detail || "上传失败" }, { status: response.status });
        }

        return redirect("/?upload=success");
    } catch (error) {
        console.error("Upload error:", error);
        return json({ error: "上传时发生错误" }, { status: 500 });
    }
};

export default function Upload() {
    const actionData = useActionData<{ error?: string }>();

    return (
        <div className="max-w-lg mx-auto my-12 p-6 bg-white rounded-lg shadow-md">
            <h1 className="text-2xl font-bold mb-6">上传文档</h1>

            {actionData?.error && (
                <div className="mb-4 p-3 text-red-700 bg-red-100 rounded border border-red-200">
                    {actionData.error}
                </div>
            )}

            <Form method="post" encType="multipart/form-data" className="space-y-4">
                <div>
                    <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-1">
                        选择文件
                    </label>
                    <input
                        id="file"
                        name="file"
                        type="file"
                        accept=".pdf,.txt,.docx,.md"
                        className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:text-sm file:bg-primary-600 file:text-white hover:file:bg-primary-700"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                        支持的格式: PDF, TXT, DOCX, Markdown
                    </p>
                </div>

                <div>
                    <label htmlFor="collection_name" className="block text-sm font-medium text-gray-700 mb-1">
                        集合名称
                    </label>
                    <input
                        id="collection_name"
                        name="collection_name"
                        type="text"
                        defaultValue="document_collection"
                        className="input w-full"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                        用于组织向量索引的集合名称
                    </p>
                </div>

                <div className="flex gap-4">
                    <button
                        type="submit"
                        className="btn btn-primary"
                    >
                        上传文档
                    </button>
                    <a
                        href="/"
                        className="btn btn-secondary flex items-center justify-center"
                    >
                        返回
                    </a>
                </div>
            </Form>
        </div>
    );
} 