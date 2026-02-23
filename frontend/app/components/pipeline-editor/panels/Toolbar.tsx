"use client";

import { useState, useRef, useEffect } from "react";
import { AVAILABLE_ROLES, getRoleConfig } from "../utils/nodeDefaults";

interface ToolbarProps {
  onAddNode: (role: string) => void;
  onRun: () => void;
  onSave: () => void;
  onLoad: () => void;
  onClear: () => void;
  isRunning: boolean;
  nodeCount: number;
}

export default function Toolbar({
  onAddNode,
  onRun,
  onSave,
  onLoad,
  onClear,
  isRunning,
  nodeCount,
}: ToolbarProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showDropdown) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showDropdown]);

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-gray-900 border-b border-gray-700">
      {/* Add Node dropdown */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded transition-colors"
        >
          + Add Node
        </button>
        {showDropdown && (
          <div className="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-600 rounded shadow-lg z-50 min-w-[180px]">
            {AVAILABLE_ROLES.map((role) => {
              const config = getRoleConfig(role);
              return (
                <button
                  key={role}
                  onClick={() => {
                    onAddNode(role);
                    setShowDropdown(false);
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-gray-200 hover:bg-gray-700 flex items-center gap-2"
                >
                  <span>{config.icon}</span>
                  <span>{config.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-700" />

      {/* Run */}
      <button
        onClick={onRun}
        disabled={isRunning || nodeCount === 0}
        className="px-3 py-1.5 bg-green-700 hover:bg-green-600 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
      >
        {isRunning ? "Running..." : "Run"}
      </button>

      {/* Save / Load */}
      <button
        onClick={onSave}
        disabled={nodeCount === 0}
        className="px-3 py-1.5 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
      >
        Save
      </button>
      <button
        onClick={onLoad}
        className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm rounded transition-colors"
      >
        Load
      </button>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-700" />

      {/* Clear */}
      <button
        onClick={onClear}
        disabled={nodeCount === 0}
        className="px-3 py-1.5 bg-gray-700 hover:bg-red-700 disabled:cursor-not-allowed text-gray-300 hover:text-white text-sm rounded transition-colors"
      >
        Clear
      </button>

      {/* Node count */}
      <span className="text-xs text-gray-500 ml-auto">
        {nodeCount} node{nodeCount !== 1 ? "s" : ""}
      </span>
    </div>
  );
}
