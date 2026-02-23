"use client";

import { useCallback, useRef, useState } from "react";
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
  const [sharedTemplates, setSharedTemplates] = useState<TemplateListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [sharedLoading, setSharedLoading] = useState(false);
  const lastFetchRef = useRef(0);
  const lastSharedFetchRef = useRef(0);
  const CACHE_TTL = 30000; // 30 seconds

  const fetchTemplates = useCallback(async (force = false) => {
    if (!force && Date.now() - lastFetchRef.current < CACHE_TTL && templates.length > 0) {
      return;
    }
    setLoading(true);
    try {
      const data = await apiFetch<TemplateListItem[]>("/api/v1/templates");
      setTemplates(data);
      lastFetchRef.current = Date.now();
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    } finally {
      setLoading(false);
    }
  }, [templates.length]);

  const fetchSharedTemplates = useCallback(async (force = false) => {
    if (!force && Date.now() - lastSharedFetchRef.current < CACHE_TTL && sharedTemplates.length > 0) {
      return;
    }
    setSharedLoading(true);
    try {
      const data = await apiFetch<TemplateListItem[]>("/api/v1/templates/shared");
      setSharedTemplates(data);
      lastSharedFetchRef.current = Date.now();
    } catch (error) {
      console.error("Failed to fetch shared templates:", error);
    } finally {
      setSharedLoading(false);
    }
  }, [sharedTemplates.length]);

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
        await fetchTemplates(true);
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
        await fetchTemplates(true);
      } catch (error) {
        console.error("Failed to delete template:", error);
        throw error;
      }
    },
    [fetchTemplates]
  );

  const forkTemplate = useCallback(
    async (id: string) => {
      try {
        await apiFetch(`/api/v1/templates/${id}/fork`, { method: "POST" });
        await fetchTemplates(true);
      } catch (error) {
        console.error("Failed to fork template:", error);
        throw error;
      }
    },
    [fetchTemplates]
  );

  const shareTemplate = useCallback(
    async (id: string, isPublic: boolean) => {
      try {
        await apiFetch(`/api/v1/templates/${id}`, {
          method: "PUT",
          body: JSON.stringify({ is_public: isPublic }),
        });
        await fetchTemplates(true);
      } catch (error) {
        console.error("Failed to update template sharing:", error);
        throw error;
      }
    },
    [fetchTemplates]
  );

  return {
    templates,
    sharedTemplates,
    loading,
    sharedLoading,
    fetchTemplates,
    fetchSharedTemplates,
    loadTemplate,
    saveTemplate,
    deleteTemplate,
    forkTemplate,
    shareTemplate,
  };
}
