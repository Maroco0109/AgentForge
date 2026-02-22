"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
} from "reactflow";
import "reactflow/dist/style.css";

import { nodeTypes } from "./nodes/AgentNodeTypes";
import { useFlowState } from "./hooks/useFlowState";
import { usePipelineExecution } from "./hooks/usePipelineExecution";
import { useTemplates } from "./hooks/useTemplates";
import { flowToDesign } from "./utils/flowToDesign";
import { designToFlow } from "./utils/designToFlow";
import type { AgentNodeData } from "./nodes/AgentNode";

import Toolbar from "./panels/Toolbar";
import PropertyPanel from "./panels/PropertyPanel";
import TemplateListPanel from "./panels/TemplateListPanel";

interface PipelineEditorProps {
  onError?: (message: string) => void;
  onEditorReady?: (loadDesign: (design: Record<string, unknown>) => void) => void;
}

export default function PipelineEditor({ onError, onEditorReady }: PipelineEditorProps) {
  const {
    nodes,
    edges,
    setNodes,
    setEdges,
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
  } = useFlowState();

  const [templateMode, setTemplateMode] = useState<"save" | "load" | null>(
    null
  );

  const {
    templates,
    loading: templatesLoading,
    fetchTemplates,
    loadTemplate,
    saveTemplate,
    deleteTemplate,
  } = useTemplates();

  const nodeNameToIdMap = useCallback(() => {
    const map = new Map<string, string>();
    for (const node of nodes) {
      map.set(node.data.name, node.id);
    }
    return map;
  }, [nodes]);

  const updateNodeStatus = useCallback(
    (nodeId: string, status: AgentNodeData["status"]) => {
      updateNodeData(nodeId, { status });
    },
    [updateNodeData]
  );

  const { isRunning, executeFromEditor } = usePipelineExecution(
    updateNodeStatus,
    setAllNodesStatus,
    nodeNameToIdMap
  );

  const handleRun = useCallback(async () => {
    try {
      const design = flowToDesign(nodes, edges);
      await executeFromEditor(design);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Pipeline execution failed";
      onError?.(msg);
    }
  }, [nodes, edges, executeFromEditor, onError]);

  const handleSaveTemplate = useCallback(
    async (name: string, description: string) => {
      try {
        const design = flowToDesign(nodes, edges);
        await saveTemplate({
          name,
          description,
          graph_data: {
            nodes: nodes.map((n) => ({
              id: n.id,
              type: n.type,
              position: n.position,
              data: n.data,
            })),
            edges: edges.map((e) => ({
              id: e.id,
              source: e.source,
              target: e.target,
            })),
          },
          design_data: design as unknown as Record<string, unknown>,
        });
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Failed to save template";
        onError?.(msg);
      }
    },
    [nodes, edges, saveTemplate, onError]
  );

  const handleLoadTemplate = useCallback(
    async (id: string) => {
      const template = await loadTemplate(id);
      if (!template) {
        onError?.("Failed to load template");
        return;
      }

      const graphData = template.graph_data;
      if (graphData?.nodes && Array.isArray(graphData.nodes) && graphData?.edges && Array.isArray(graphData.edges)) {
        setNodes(
          (graphData.nodes as Node<AgentNodeData>[]).map((n) => ({
            ...n,
            data: { ...n.data, status: "idle" as const },
          }))
        );
        setEdges(graphData.edges as Edge[]);
      } else if (template.design_data) {
        const design = template.design_data as {
          name: string;
          description: string;
          agents: { name: string; role: string; llm_model: string; description: string }[];
        };
        const { nodes: newNodes, edges: newEdges } = designToFlow(design);
        setNodes(newNodes);
        setEdges(newEdges);
      }
    },
    [loadTemplate, setNodes, setEdges, onError]
  );

  // Load design from chat (called externally)
  const loadDesign = useCallback(
    (design: { name: string; description: string; agents: { name: string; role: string; llm_model: string; description: string }[] }) => {
      const { nodes: newNodes, edges: newEdges } = designToFlow(design);
      setNodes(newNodes);
      setEdges(newEdges);
    },
    [setNodes, setEdges]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNodeId(node.id);
    },
    [setSelectedNodeId]
  );

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, [setSelectedNodeId]);

  // Expose loadDesign to parent via callback
  useEffect(() => {
    onEditorReady?.((design: Record<string, unknown>) => {
      loadDesign(design as Parameters<typeof loadDesign>[0]);
    });
  }, [loadDesign, onEditorReady]);

  const miniMapNodeColor = useMemo(
    () => (node: Node) => {
      const data = node.data as AgentNodeData;
      if (data.status === "running") return "#3b82f6";
      if (data.status === "completed") return "#10b981";
      if (data.status === "failed") return "#ef4444";
      return "#6b7280";
    },
    []
  );

  return (
    <div className="h-full flex flex-col relative">
      <Toolbar
        onAddNode={addNode}
        onRun={handleRun}
        onSave={() => setTemplateMode("save")}
        onLoad={() => setTemplateMode("load")}
        onClear={clearAll}
        isRunning={isRunning}
        nodeCount={nodes.length}
      />

      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          className="bg-gray-950"
          defaultEdgeOptions={{ animated: true }}
        >
          <Background color="#374151" gap={20} />
          <Controls className="!bg-gray-800 !border-gray-600 !shadow-lg [&>button]:!bg-gray-700 [&>button]:!border-gray-600 [&>button]:!text-gray-300 [&>button:hover]:!bg-gray-600" />
          <MiniMap
            nodeColor={miniMapNodeColor}
            className="!bg-gray-900 !border-gray-700"
            maskColor="rgba(0, 0, 0, 0.6)"
          />
        </ReactFlow>

        <PropertyPanel
          node={selectedNode}
          onUpdate={updateNodeData}
          onDelete={(id) => {
            deleteNode(id);
            setSelectedNodeId(null);
          }}
          onClose={() => setSelectedNodeId(null)}
        />
      </div>

      {templateMode && (
        <TemplateListPanel
          mode={templateMode}
          templates={templates}
          loading={templatesLoading}
          onClose={() => setTemplateMode(null)}
          onSave={handleSaveTemplate}
          onLoad={handleLoadTemplate}
          onDelete={deleteTemplate}
          onRefresh={fetchTemplates}
        />
      )}
    </div>
  );
}
