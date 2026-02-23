"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

interface TemplateListItem {
  id: string;
  name: string;
  description: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<TemplateListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const router = useRouter();

  const fetchTemplates = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await apiFetch<TemplateListItem[]>("/api/v1/templates");
      setTemplates(data);
    } catch (err) {
      console.error("Failed to fetch templates:", err);
      setError(err instanceof Error ? err.message : "Failed to load templates");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const filteredTemplates = templates.filter((t) =>
    searchQuery
      ? t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.description && t.description.toLowerCase().includes(searchQuery.toLowerCase()))
      : true
  );

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-100">Templates</h1>
          <button
            onClick={() => router.push("/pipeline-editor")}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-md font-medium transition-colors"
          >
            New Template
          </button>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search templates..."
            className="w-full bg-gray-900 text-gray-100 border border-gray-700 rounded-md px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent placeholder:text-gray-500"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-md px-4 py-3 flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={fetchTemplates}
              className="text-red-300 hover:text-red-100 text-xs underline ml-4"
            >
              Retry
            </button>
          </div>
        )}

        {/* Template grid */}
        {isLoading ? (
          <div className="text-center text-gray-500 py-12">Loading templates...</div>
        ) : filteredTemplates.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">
              {searchQuery ? "No templates match your search" : "No templates yet. Click \"New Template\" to get started."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredTemplates.map((template) => (
              <button
                key={template.id}
                onClick={() => router.push(`/templates/${template.id}`)}
                className="text-left bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg px-5 py-4 transition-colors group"
              >
                <div className="flex items-start justify-between">
                  <h3 className="text-sm font-medium text-gray-200 group-hover:text-gray-100">
                    {template.name}
                  </h3>
                  {template.is_public && (
                    <span className="text-[10px] bg-green-900/50 text-green-400 px-1.5 py-0.5 rounded flex-shrink-0 ml-2">
                      Public
                    </span>
                  )}
                </div>
                {template.description && (
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{template.description}</p>
                )}
                <p className="text-xs text-gray-600 mt-2">
                  {new Date(template.updated_at).toLocaleDateString()}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
