"use client";

import { use, useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { apiFetch } from "@/lib/api";

const ReactFlow = dynamic(
  () => import("reactflow").then((mod) => mod.default),
  { ssr: false }
);

// Import ReactFlow CSS
import "reactflow/dist/style.css";

interface TemplateDetail {
  id: string;
  name: string;
  description: string | null;
  is_public: boolean;
  graph_data: { nodes: unknown[]; edges: unknown[] };
  design_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface TemplateDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function TemplateDetailPage({ params }: TemplateDetailPageProps) {
  const { id } = use(params);
  const [template, setTemplate] = useState<TemplateDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isForkLoading, setIsForkLoading] = useState(false);
  const router = useRouter();

  const fetchTemplate = useCallback(async () => {
    try {
      const data = await apiFetch<TemplateDetail>(`/api/v1/templates/${id}`);
      setTemplate(data);
    } catch (error) {
      console.error("Failed to fetch template:", error);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  const handleFork = async () => {
    setIsForkLoading(true);
    try {
      await apiFetch(`/api/v1/templates/${id}/fork`, { method: "POST" });
      router.push("/templates");
    } catch (error) {
      console.error("Failed to fork template:", error);
    } finally {
      setIsForkLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-gray-500">Loading template...</div>
      </div>
    );
  }

  if (!template) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-gray-500">Template not found</div>
      </div>
    );
  }

  const nodes = (template.graph_data?.nodes || []) as Array<{
    id: string;
    position: { x: number; y: number };
    data: Record<string, unknown>;
    type?: string;
  }>;
  const edges = (template.graph_data?.edges || []) as Array<{
    id: string;
    source: string;
    target: string;
    type?: string;
  }>;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <button
              onClick={() => router.push("/templates")}
              className="text-sm text-gray-500 hover:text-gray-300 mb-2 inline-block"
            >
              ← Back to Templates
            </button>
            <h1 className="text-2xl font-bold text-gray-100">{template.name}</h1>
            {template.description && (
              <p className="text-sm text-gray-400 mt-1">{template.description}</p>
            )}
          </div>
          <button
            onClick={handleFork}
            disabled={isForkLoading}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-700 text-white text-sm rounded-md font-medium transition-colors"
          >
            {isForkLoading ? "Forking..." : "Fork"}
          </button>
        </div>

        {/* Info */}
        <div className="flex gap-4 mb-6 text-xs text-gray-500">
          <span>Created: {new Date(template.created_at).toLocaleDateString()}</span>
          <span>Updated: {new Date(template.updated_at).toLocaleDateString()}</span>
          {template.is_public && (
            <span className="text-green-400">Public</span>
          )}
        </div>

        {/* Pipeline diagram */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden" style={{ height: "500px" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            className="bg-gray-950"
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            zoomOnScroll={false}
            panOnScroll={false}
          />
        </div>
      </div>
    </div>
  );
}
