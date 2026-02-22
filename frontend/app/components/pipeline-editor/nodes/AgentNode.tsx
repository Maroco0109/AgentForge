"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { getRoleConfig } from "../utils/nodeDefaults";

export interface AgentNodeData {
  name: string;
  role: string;
  llmModel: string;
  description: string;
  status: "idle" | "running" | "completed" | "failed";
  // Phase 8B extended fields
  customPrompt?: string;
  temperature?: number;
  maxTokens?: number;
  retryCount?: number;
  isCustomRole?: boolean;
}

function AgentNodeComponent({ data, selected }: NodeProps<AgentNodeData>) {
  const config = getRoleConfig(data.role);
  const statusStyles: Record<string, string> = {
    idle: "border-gray-600",
    running: "border-blue-500 agent-node-running",
    completed: "border-green-500",
    failed: "border-red-500",
  };

  const hasAdvancedConfig =
    data.customPrompt ||
    (data.temperature !== undefined && data.temperature !== 0.7) ||
    (data.maxTokens !== undefined && data.maxTokens !== 4096) ||
    (data.retryCount !== undefined && data.retryCount !== 3);

  return (
    <div
      className={`bg-gray-800 rounded-lg border-2 ${statusStyles[data.status] || statusStyles.idle} ${
        selected ? "ring-2 ring-primary-500" : ""
      } min-w-[180px] shadow-lg`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-gray-400 !w-3 !h-3 !border-2 !border-gray-600"
      />

      {/* Header */}
      <div
        className="px-3 py-2 rounded-t-md text-white text-xs font-semibold flex items-center gap-1.5"
        style={{ backgroundColor: config.color }}
      >
        <span>{config.icon}</span>
        <span>{config.label}</span>
        {data.isCustomRole && (
          <span className="ml-auto text-[10px] opacity-75">custom</span>
        )}
        {hasAdvancedConfig && (
          <span className="ml-auto text-[10px]" title="Advanced settings configured">
            {"\u2699"}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        <div className="text-gray-100 text-sm font-medium truncate">
          {data.name}
        </div>
        <div className="text-gray-400 text-xs mt-1 truncate">
          {data.llmModel}
        </div>
        {data.status === "running" && (
          <div className="text-blue-400 text-xs mt-1 flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
            Running...
          </div>
        )}
        {data.status === "completed" && (
          <div className="text-green-400 text-xs mt-1">Completed</div>
        )}
        {data.status === "failed" && (
          <div className="text-red-400 text-xs mt-1">Failed</div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-gray-400 !w-3 !h-3 !border-2 !border-gray-600"
      />
    </div>
  );
}

export default memo(AgentNodeComponent);
