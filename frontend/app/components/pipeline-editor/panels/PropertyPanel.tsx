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

  useEffect(() => {
    if (node) {
      setName(node.data.name);
      setRole(node.data.role);
      setLlmModel(node.data.llmModel);
      setDescription(node.data.description);
    }
  }, [node]);

  if (!node) return null;

  const handleApply = () => {
    onUpdate(node.id, { name, role, llmModel, description });
  };

  const config = getRoleConfig(role);

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

        {/* Role */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Role</label>
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
