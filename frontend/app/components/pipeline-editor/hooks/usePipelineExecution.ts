"use client";

import { useCallback, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { DesignProposal } from "../utils/flowToDesign";

interface PipelineStatus {
  pipeline_id: string;
  status: string;
  design_name: string;
  started_at: string;
}

export function usePipelineExecution(
  updateNodeStatus: (nodeId: string, status: "running" | "completed" | "failed") => void,
  setAllNodesStatus: (status: "idle" | "running" | "completed" | "failed") => void,
  nodeNameToIdMap: () => Map<string, string>
) {
  const [isRunning, setIsRunning] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const wsListenerRef = useRef<((event: MessageEvent) => void) | null>(null);

  const executeFromEditor = useCallback(
    async (design: DesignProposal) => {
      setIsRunning(true);
      setAllNodesStatus("idle");

      try {
        const result = await apiFetch<PipelineStatus>(
          "/api/v1/pipelines/execute-direct",
          {
            method: "POST",
            body: JSON.stringify({ design }),
          }
        );

        if (result.status === "completed") {
          setAllNodesStatus("completed");
        } else if (result.status === "failed") {
          setAllNodesStatus("failed");
        }

        return result;
      } catch (error) {
        setAllNodesStatus("failed");
        throw error;
      } finally {
        setIsRunning(false);
        setCurrentAgent(null);
      }
    },
    [setAllNodesStatus]
  );

  // TODO: Wire attachWsListener to shared WebSocket in Phase 8B
  // for real-time node status updates during chat-initiated pipeline runs.
  const attachWsListener = useCallback(
    (ws: WebSocket) => {
      // Remove previous listener if any
      if (wsListenerRef.current) {
        ws.removeEventListener("message", wsListenerRef.current);
      }

      const listener = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          const nameMap = nodeNameToIdMap();

          if (data.type === "pipeline_started") {
            setIsRunning(true);
            setAllNodesStatus("idle");
          }

          if (data.type === "agent_completed") {
            const agentName = data.agent_name as string;
            setCurrentAgent(agentName);
            const nodeId = nameMap.get(agentName);
            if (nodeId) {
              updateNodeStatus(nodeId, "completed");
            }
          }

          if (data.type === "pipeline_result") {
            setIsRunning(false);
            setCurrentAgent(null);
            setAllNodesStatus("completed");
          }

          if (data.type === "pipeline_failed") {
            setIsRunning(false);
            setCurrentAgent(null);
          }
        } catch {
          // Ignore non-JSON messages
        }
      };

      ws.addEventListener("message", listener);
      wsListenerRef.current = listener;
    },
    [nodeNameToIdMap, setAllNodesStatus, updateNodeStatus]
  );

  return {
    isRunning,
    currentAgent,
    executeFromEditor,
    attachWsListener,
  };
}
