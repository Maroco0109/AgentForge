"use client";

import { useCallback, useState } from "react";
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "reactflow";
import type { AgentNodeData } from "../nodes/AgentNode";
import { getRoleConfig } from "../utils/nodeDefaults";

function nextNodeId(): string {
  return `agent-${crypto.randomUUID().slice(0, 8)}`;
}

export function useFlowState() {
  const [nodes, setNodes] = useState<Node<AgentNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    []
  );

  const addNode = useCallback(
    (role: string) => {
      const config = getRoleConfig(role);
      const id = nextNodeId();
      const newNode: Node<AgentNodeData> = {
        id,
        type: "agentNode",
        position: {
          x: 250 + Math.random() * 100,
          y: nodes.length * 150 + 50,
        },
        data: {
          name: `${config.label}_${id.split("-")[1]}`,
          role,
          llmModel: config.defaultModel,
          description: "",
          status: "idle",
        },
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [nodes.length]
  );

  const updateNodeData = useCallback(
    (nodeId: string, data: Partial<AgentNodeData>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n
        )
      );
    },
    []
  );

  const deleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) =>
        eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
      );
      if (selectedNodeId === nodeId) {
        setSelectedNodeId(null);
      }
    },
    [selectedNodeId]
  );

  const clearAll = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setSelectedNodeId(null);
  }, []);

  const setAllNodesStatus = useCallback(
    (status: AgentNodeData["status"]) => {
      setNodes((nds) =>
        nds.map((n) => ({ ...n, data: { ...n.data, status } }))
      );
    },
    []
  );

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;

  return {
    nodes,
    edges,
    setNodes,
    setEdges,
    selectedNodeId,
    selectedNode,
    setSelectedNodeId,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNodeData,
    deleteNode,
    clearAll,
    setAllNodesStatus,
  };
}
