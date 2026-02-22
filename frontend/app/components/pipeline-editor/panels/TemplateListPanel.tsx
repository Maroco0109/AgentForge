"use client";

import { useEffect, useState } from "react";
import type { TemplateListItem } from "../hooks/useTemplates";

interface TemplateListPanelProps {
  mode: "save" | "load";
  templates: TemplateListItem[];
  sharedTemplates: TemplateListItem[];
  loading: boolean;
  onClose: () => void;
  onSave: (name: string, description: string) => void;
  onLoad: (id: string) => void;
  onDelete: (id: string) => void;
  onFork: (id: string) => void;
  onShare: (id: string, isPublic: boolean) => void;
  onRefresh: () => void;
  onRefreshShared: () => void;
}

export default function TemplateListPanel({
  mode,
  templates,
  sharedTemplates,
  loading,
  onClose,
  onSave,
  onLoad,
  onDelete,
  onFork,
  onShare,
  onRefresh,
  onRefreshShared,
}: TemplateListPanelProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [activeTab, setActiveTab] = useState<"my" | "shared">("my");

  useEffect(() => {
    onRefresh();
  }, [onRefresh]);

  useEffect(() => {
    if (activeTab === "shared") {
      onRefreshShared();
    }
  }, [activeTab, onRefreshShared]);

  const handleSave = () => {
    if (!name.trim()) return;
    onSave(name.trim(), description.trim());
    onClose();
  };

  const displayList = activeTab === "my" ? templates : sharedTemplates;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-lg shadow-2xl w-[480px] max-h-[70vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-gray-100">
            {mode === "save" ? "Save Template" : "Load Template"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 text-xl"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {mode === "save" && (
            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Template Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="My Pipeline Template"
                  className="w-full bg-gray-800 text-gray-100 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Description (optional)
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full bg-gray-800 text-gray-100 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none"
                />
              </div>
              <button
                onClick={handleSave}
                disabled={!name.trim()}
                className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white py-2 rounded text-sm transition-colors"
              >
                Save Template
              </button>
            </div>
          )}

          {/* Tab bar (load mode only) */}
          {mode === "load" && (
            <div className="flex gap-1 mb-3 border-b border-gray-700">
              <button
                onClick={() => setActiveTab("my")}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  activeTab === "my"
                    ? "text-primary-400 border-b-2 border-primary-400"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                My Templates
              </button>
              <button
                onClick={() => setActiveTab("shared")}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  activeTab === "shared"
                    ? "text-primary-400 border-b-2 border-primary-400"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Shared Templates
              </button>
            </div>
          )}

          {/* Template list */}
          <div>
            {loading ? (
              <div className="text-center text-gray-500 py-6 text-sm">
                Loading...
              </div>
            ) : displayList.length === 0 ? (
              <div className="text-center text-gray-500 py-6 text-sm">
                {activeTab === "my"
                  ? "No templates saved yet"
                  : "No shared templates available"}
              </div>
            ) : (
              <div className="space-y-2">
                {displayList.map((t) => (
                  <div
                    key={t.id}
                    className="bg-gray-800 rounded px-3 py-2.5 flex items-center justify-between"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-gray-100 font-medium truncate flex items-center gap-1.5">
                        {t.name}
                        {activeTab === "my" && t.is_public && (
                          <span className="text-[10px] bg-green-900/50 text-green-400 px-1.5 py-0.5 rounded">
                            Public
                          </span>
                        )}
                      </div>
                      {t.description && (
                        <div className="text-xs text-gray-400 truncate">
                          {t.description}
                        </div>
                      )}
                      <div className="text-xs text-gray-500 mt-0.5">
                        {new Date(t.updated_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex gap-1.5 ml-2">
                      {activeTab === "my" && mode === "load" && (
                        <button
                          onClick={() => {
                            onLoad(t.id);
                            onClose();
                          }}
                          className="px-2.5 py-1 bg-primary-600 hover:bg-primary-700 text-white text-xs rounded transition-colors"
                        >
                          Load
                        </button>
                      )}
                      {activeTab === "my" && (
                        <button
                          onClick={() => onShare(t.id, !t.is_public)}
                          className="px-2.5 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded transition-colors"
                          title={t.is_public ? "Make private" : "Make public"}
                        >
                          {t.is_public ? "Unshare" : "Share"}
                        </button>
                      )}
                      {activeTab === "shared" && (
                        <button
                          onClick={() => onFork(t.id)}
                          className="px-2.5 py-1 bg-primary-600 hover:bg-primary-700 text-white text-xs rounded transition-colors"
                        >
                          Fork
                        </button>
                      )}
                      {activeTab === "my" && (
                        <button
                          onClick={() => {
                            if (window.confirm("Delete this template?")) {
                              onDelete(t.id);
                            }
                          }}
                          className="px-2.5 py-1 bg-gray-700 hover:bg-red-700 text-gray-300 hover:text-white text-xs rounded transition-colors"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
