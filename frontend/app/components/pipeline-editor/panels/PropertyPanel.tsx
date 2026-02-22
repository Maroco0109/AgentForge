"use client";

import type { Node } from "reactflow";
import type { AgentNodeData } from "../nodes/AgentNode";
import { AVAILABLE_MODELS, AVAILABLE_ROLES, getRoleConfig } from "../utils/nodeDefaults";
import { useState, useEffect } from "react";

interface PropertyPanelProps {
  node: Node<AgentNodeData> | null;
  onUpdate: (nodeId: string, data: Partial<AgentNodeData>) => void;
  onDelete: (nodeId: string) => void;
  onClose: () => void;
}

export default function PropertyPanel({
  node,
  onUpdate,
  onDelete,
  onClose,
}: PropertyPanelProps) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [description, setDescription] = useState("");
  const [isCustomRole, setIsCustomRole] = useState(false);
  const [customRoleName, setCustomRoleName] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [retryCount, setRetryCount] = useState(3);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (node) {
      setName(node.data.name);
      setRole(node.data.role);
      setLlmModel(node.data.llmModel);
      setDescription(node.data.description);
      setIsCustomRole(node.data.isCustomRole || false);
      setCustomRoleName(node.data.isCustomRole ? node.data.role : "");
      setCustomPrompt(node.data.customPrompt || "");
      setTemperature(node.data.temperature ?? 0.7);
      setMaxTokens(node.data.maxTokens ?? 4096);
      setRetryCount(node.data.retryCount ?? 3);
      // Auto-expand if advanced settings are configured
      setShowAdvanced(
        !!(
          node.data.customPrompt ||
          (node.data.temperature !== undefined && node.data.temperature !== 0.7) ||
          (node.data.maxTokens !== undefined && node.data.maxTokens !== 4096) ||
          (node.data.retryCount !== undefined && node.data.retryCount !== 3)
        )
      );
    }
  }, [node]);

  if (!node) return null;

  const handleApply = () => {
    const effectiveRole = isCustomRole ? customRoleName || "custom" : role;
    onUpdate(node.id, {
      name,
      role: effectiveRole,
      llmModel,
      description,
      isCustomRole,
      customPrompt: customPrompt || undefined,
      temperature,
      maxTokens,
      retryCount,
    });
  };

  const config = getRoleConfig(isCustomRole ? "" : role);

  return (
    <div className="absolute right-0 top-0 h-full w-72 bg-gray-900 border-l border-gray-700 shadow-xl z-20 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-gray-200">Node Properties</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-200 text-lg"
        >
          &times;
        </button>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Color indicator */}
        <div
          className="h-1 rounded"
          style={{ backgroundColor: config.color }}
        />

        {/* Name */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-gray-800 text-gray-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        {/* Custom Role Toggle */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="customRoleToggle"
            checked={isCustomRole}
            onChange={(e) => setIsCustomRole(e.target.checked)}
            className="rounded bg-gray-800 border-gray-600"
          />
          <label htmlFor="customRoleToggle" className="text-xs text-gray-400">
            Custom Role
          </label>
        </div>

        {/* Role */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Role</label>
          {isCustomRole ? (
            <input
              type="text"
              value={customRoleName}
              onChange={(e) => setCustomRoleName(e.target.value)}
              placeholder="e.g. summarizer"
              className="w-full bg-gray-800 text-gray-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          ) : (
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full bg-gray-800 text-gray-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              {AVAILABLE_ROLES.map((r) => (
                <option key={r} value={r}>
                  {getRoleConfig(r).icon} {getRoleConfig(r).label}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* LLM Model */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">LLM Model</label>
          <select
            value={llmModel}
            onChange={(e) => setLlmModel(e.target.value)}
            className="w-full bg-gray-800 text-gray-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {AVAILABLE_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full bg-gray-800 text-gray-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none"
          />
        </div>

        {/* Advanced Settings Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full text-left text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 py-1"
        >
          <span
            className="transition-transform inline-block"
            style={{ transform: showAdvanced ? "rotate(90deg)" : "rotate(0deg)" }}
          >
            ▶
          </span>
          Advanced Settings
        </button>

        {showAdvanced && (
          <div className="space-y-3 pl-2 border-l border-gray-700">
            {/* Custom Prompt */}
            {isCustomRole && (
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Custom System Prompt
                </label>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  rows={3}
                  placeholder="Custom system prompt for this agent..."
                  className="w-full bg-gray-800 text-gray-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none"
                />
              </div>
            )}

            {/* Temperature */}
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Temperature: {temperature.toFixed(1)}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-primary-500"
              />
              <div className="flex justify-between text-[10px] text-gray-500">
                <span>Precise (0)</span>
                <span>Creative (2)</span>
              </div>
            </div>

            {/* Max Tokens */}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Max Tokens</label>
              <input
                type="number"
                min="1"
                max="16384"
                value={maxTokens}
                onChange={(e) => setMaxTokens(Math.max(1, Math.min(16384, parseInt(e.target.value) || 1)))}
                className="w-full bg-gray-800 text-gray-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>

            {/* Retry Count */}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Retry Count</label>
              <input
                type="number"
                min="0"
                max="10"
                value={retryCount}
                onChange={(e) => setRetryCount(Math.max(0, Math.min(10, parseInt(e.target.value) || 0)))}
                className="w-full bg-gray-800 text-gray-100 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t border-gray-700 flex gap-2">
        <button
          onClick={handleApply}
          className="flex-1 bg-primary-600 hover:bg-primary-700 text-white text-sm py-1.5 rounded transition-colors"
        >
          Apply
        </button>
        <button
          onClick={() => onDelete(node.id)}
          className="px-3 bg-red-700 hover:bg-red-600 text-white text-sm py-1.5 rounded transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
