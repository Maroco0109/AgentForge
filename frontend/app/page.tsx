"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import ChatWindow from "./components/ChatWindow";
import SplitView from "./components/SplitView";

const PipelineEditor = dynamic(
  () => import("./components/pipeline-editor/PipelineEditor"),
  { ssr: false }
);

const EDITOR_OPEN_KEY = "agentforge-editor-open";

export default function Home() {
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const loadDesignRef = useRef<((design: Record<string, unknown>) => void) | null>(null);

  // Restore editor open state from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(EDITOR_OPEN_KEY);
      if (saved === "true") setIsEditorOpen(true);
    } catch {
      // Ignore
    }
  }, []);

  // Persist editor open state
  useEffect(() => {
    try {
      localStorage.setItem(EDITOR_OPEN_KEY, String(isEditorOpen));
    } catch {
      // Ignore
    }
  }, [isEditorOpen]);

  const handleEditorReady = useCallback((loadDesign: (design: Record<string, unknown>) => void) => {
    loadDesignRef.current = loadDesign;
  }, []);

  const handleOpenDesign = useCallback((design: Record<string, unknown>) => {
    setIsEditorOpen(true);
    loadDesignRef.current?.(design);
  }, []);

  return (
    <main className="min-h-screen bg-gray-950 flex flex-col">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-100">AgentForge</h1>
        <p className="text-sm text-gray-400 mt-1">User-prompt driven multi-agent platform</p>
      </header>
      <div className="flex-1 overflow-hidden">
        <SplitView
          left={<ChatWindow onOpenDesign={handleOpenDesign} />}
          right={<PipelineEditor onEditorReady={handleEditorReady} />}
          isEditorOpen={isEditorOpen}
          onEditorToggle={setIsEditorOpen}
        />
      </div>
    </main>
  );
}
