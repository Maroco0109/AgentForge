"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface SplitViewProps {
  left: React.ReactNode;
  right: React.ReactNode;
  isEditorOpen: boolean;
  onEditorToggle: (open: boolean) => void;
}

const MIN_PANEL_WIDTH = 300;
const STORAGE_KEY = "agentforge-split-view";

export default function SplitView({ left, right, isEditorOpen, onEditorToggle }: SplitViewProps) {
  const [splitRatio, setSplitRatio] = useState(0.5);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  // Restore splitRatio from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.ratio === "number") setSplitRatio(parsed.ratio);
      }
    } catch {
      // Ignore parse errors
    }
  }, []);

  // Save splitRatio
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ratio: splitRatio }));
    } catch {
      // Ignore storage errors
    }
  }, [splitRatio]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const ratio = Math.max(
        MIN_PANEL_WIDTH / rect.width,
        Math.min(1 - MIN_PANEL_WIDTH / rect.width, x / rect.width)
      );
      setSplitRatio(ratio);
    };

    const handleMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  return (
    <div ref={containerRef} className="h-full flex relative">
      {/* Left panel (Chat) */}
      <div
        className="h-full overflow-hidden"
        style={{ width: isEditorOpen ? `${splitRatio * 100}%` : "100%" }}
      >
        {left}
      </div>

      {isEditorOpen && (
        <>
          {/* Resize handle */}
          <div
            onMouseDown={handleMouseDown}
            className="w-1.5 bg-gray-800 hover:bg-primary-600 cursor-col-resize flex-shrink-0 transition-colors relative group"
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>

          {/* Right panel (Editor) */}
          <div
            className="h-full overflow-hidden"
            style={{ width: `${(1 - splitRatio) * 100}%` }}
          >
            {right}
          </div>
        </>
      )}

      {/* Toggle button */}
      <button
        onClick={() => onEditorToggle(!isEditorOpen)}
        className="absolute top-2 right-2 z-30 px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded border border-gray-600 transition-colors"
        title={isEditorOpen ? "Close Editor" : "Open Pipeline Editor"}
      >
        {isEditorOpen ? "Close Editor" : "Pipeline Editor"}
      </button>
    </div>
  );
}
