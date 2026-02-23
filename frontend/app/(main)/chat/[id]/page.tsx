"use client";

import { useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import ChatWindow, { type PipelineEvent } from "@/app/components/ChatWindow";
import SplitView from "@/app/components/SplitView";

const PipelineEditor = dynamic(
  () => import("@/app/components/pipeline-editor/PipelineEditor"),
  { ssr: false }
);

interface ChatPageProps {
  params: { id: string };
}

export default function ChatPage({ params }: ChatPageProps) {
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [pipelineEvents, setPipelineEvents] = useState<PipelineEvent[]>([]);
  const [editorError, setEditorError] = useState<string | null>(null);
  const loadDesignRef = useRef<((design: Record<string, unknown>) => void) | null>(null);

  const handlePipelineEvent = useCallback((event: PipelineEvent) => {
    setPipelineEvents((prev) => [...prev, event]);
  }, []);

  const handleOpenDesign = useCallback((design: Record<string, unknown>) => {
    setIsEditorOpen(true);
    // Give the editor a tick to mount if it was just opened
    setTimeout(() => {
      loadDesignRef.current?.(design);
    }, 0);
  }, []);

  const handleEditorReady = useCallback(
    (loadDesign: (design: Record<string, unknown>) => void) => {
      loadDesignRef.current = loadDesign;
    },
    []
  );

  return (
    <div className="flex-1 overflow-hidden">
      <SplitView
        isEditorOpen={isEditorOpen}
        onEditorToggle={setIsEditorOpen}
        left={
          <ChatWindow
            conversationId={params.id}
            onOpenDesign={handleOpenDesign}
            onPipelineEvent={handlePipelineEvent}
          />
        }
        right={
          <div className="h-full flex flex-col relative">
            {editorError && (
              <div className="absolute top-2 left-1/2 -translate-x-1/2 z-50 bg-red-900/90 text-red-200 text-sm px-4 py-2 rounded-md border border-red-700">
                {editorError}
                <button onClick={() => setEditorError(null)} className="ml-2 text-red-400 hover:text-red-300">&times;</button>
              </div>
            )}
            <PipelineEditor
              onError={setEditorError}
              onEditorReady={handleEditorReady}
              externalPipelineEvents={pipelineEvents}
            />
          </div>
        }
      />
    </div>
  );
}
