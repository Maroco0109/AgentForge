"use client";

import { useCallback, useState } from "react";
import { apiFetch } from "@/lib/api";

export interface TemplateListItem {
  id: string;
  name: string;
  description: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface TemplateDetail extends TemplateListItem {
  graph_data: { nodes: unknown[]; edges: unknown[] };
  design_data: Record<string, unknown>;
}

export function useTemplates() {
  const [templates, setTemplates] = useState<TemplateListItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<TemplateListItem[]>("/api/v1/templates");
      setTemplates(data);
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTemplate = useCallback(async (id: string): Promise<TemplateDetail | null> => {
    try {
      return await apiFetch<TemplateDetail>(`/api/v1/templates/${id}`);
    } catch (error) {
      console.error("Failed to load template:", error);
      return null;
    }
  }, []);

  const saveTemplate = useCallback(
    async (data: {
      name: string;
      description: string;
      graph_data: Record<string, unknown>;
      design_data: Record<string, unknown>;
    }) => {
      try {
        await apiFetch("/api/v1/templates", {
          method: "POST",
          body: JSON.stringify(data),
        });
        await fetchTemplates();
      } catch (error) {
        console.error("Failed to save template:", error);
        throw error;
      }
    },
    [fetchTemplates]
  );

  const deleteTemplate = useCallback(
    async (id: string) => {
      try {
        await apiFetch(`/api/v1/templates/${id}`, { method: "DELETE" });
        await fetchTemplates();
      } catch (error) {
        console.error("Failed to delete template:", error);
        throw error;
      }
    },
    [fetchTemplates]
  );

  return {
    templates,
    loading,
    fetchTemplates,
    loadTemplate,
    saveTemplate,
    deleteTemplate,
  };
}
