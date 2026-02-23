"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const fetchConversations = useCallback(async () => {
    try {
      const data = await apiFetch<Conversation[]>("/api/v1/conversations");
      setConversations(data);
    } catch (error) {
      console.error("Failed to fetch conversations:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleNewConversation = async () => {
    if (isCreating) return;
    setIsCreating(true);
    setError("");
    try {
      const data = await apiFetch<Conversation>("/api/v1/conversations", {
        method: "POST",
        body: JSON.stringify({ title: "New Conversation" }),
      });
      router.push(`/chat/${data.id}`);
    } catch (err) {
      console.error("Failed to create conversation:", err);
      setError(err instanceof Error ? err.message : "Failed to create conversation");
    } finally {
      setIsCreating(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);

    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${Math.floor(diffHours)}h ago`;
    if (diffHours < 168) return `${Math.floor(diffHours / 24)}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-gray-100">Conversations</h1>
          <button
            onClick={handleNewConversation}
            disabled={isCreating}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm rounded-md font-medium transition-colors"
          >
            {isCreating ? "Creating..." : "New Conversation"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        {/* List */}
        {isLoading ? (
          <div className="text-center text-gray-500 py-12">Loading conversations...</div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">No conversations yet</p>
            <button
              onClick={handleNewConversation}
              disabled={isCreating}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm rounded-md font-medium transition-colors"
            >
              {isCreating ? "Creating..." : "Start your first conversation"}
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => router.push(`/chat/${conv.id}`)}
                className="w-full text-left bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg px-5 py-4 transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-200 group-hover:text-gray-100 truncate">
                    {conv.title}
                  </h3>
                  <span className="text-xs text-gray-500 flex-shrink-0 ml-4">
                    {formatDate(conv.updated_at)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
