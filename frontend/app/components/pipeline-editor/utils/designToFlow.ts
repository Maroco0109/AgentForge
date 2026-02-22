// Convert DesignProposal to React Flow nodes + edges for visualization

import type { Edge, Node } from "reactflow";
import type { AgentNodeData } from "../nodes/AgentNode";

interface AgentSpec {
  name: string;
  role: string;
  llm_model: string;
  description: string;
  custom_prompt?: string;
  temperature?: number;
  max_tokens?: number;
  retry_count?: number;
  is_custom_role?: boolean;
}

interface EdgeSpec {
  source: string;
  target: string;
  condition?: string;
}

interface DesignProposal {
  name: string;
  description: string;
  agents: AgentSpec[];
  edges?: EdgeSpec[];
}

const VERTICAL_SPACING = 150;
const HORIZONTAL_SPACING = 220;
const X_CENTER = 300;

/**
 * Convert a DesignProposal into React Flow nodes and edges.
 * Supports sequential layout and 2D layout for parallel branches.
 */
export function designToFlow(design: DesignProposal): {
  nodes: Node<AgentNodeData>[];
  edges: Edge[];
} {
  const agentNameToId = new Map<string, string>();
  const allNodes: Node<AgentNodeData>[] = [];

  // Create nodes
  design.agents.forEach((agent, index) => {
    const nodeId = `agent-${index + 1}`;
    agentNameToId.set(agent.name, nodeId);
    allNodes.push({
      id: nodeId,
      type: "agentNode",
      position: { x: X_CENTER, y: index * VERTICAL_SPACING + 50 },
      data: {
        name: agent.name,
        role: agent.role,
        llmModel: agent.llm_model,
        description: agent.description,
        status: "idle" as const,
        customPrompt: agent.custom_prompt,
        temperature: agent.temperature,
        maxTokens: agent.max_tokens,
        retryCount: agent.retry_count,
        isCustomRole: agent.is_custom_role,
      },
    });
  });

  // Build edges
  if (design.edges && design.edges.length > 0) {
    // Explicit edge topology
    const flowEdges: Edge[] = design.edges.map((edgeSpec, idx) => {
      const sourceId = agentNameToId.get(edgeSpec.source) || edgeSpec.source;
      const targetId = agentNameToId.get(edgeSpec.target) || edgeSpec.target;
      const edge: Edge = {
        id: `edge-${idx}-${sourceId}-${targetId}`,
        source: sourceId,
        target: targetId,
        animated: false,
      };
      if (edgeSpec.condition) {
        edge.type = "conditional";
        edge.data = { condition: edgeSpec.condition };
      }
      return edge;
    });

    // 2D layout for parallel nodes
    layoutParallelNodes(allNodes, flowEdges);

    return { nodes: allNodes, edges: flowEdges };
  }

  // Sequential edges (default)
  const sequentialEdges: Edge[] = [];
  for (let i = 0; i < allNodes.length - 1; i++) {
    sequentialEdges.push({
      id: `edge-${allNodes[i].id}-${allNodes[i + 1].id}`,
      source: allNodes[i].id,
      target: allNodes[i + 1].id,
      animated: false,
    });
  }

  return { nodes: allNodes, edges: sequentialEdges };
}

/**
 * Adjust node positions for parallel branches.
 * Nodes with the same parent are laid out horizontally.
 */
function layoutParallelNodes(nodes: Node<AgentNodeData>[], edges: Edge[]): void {
  // Build parent -> children map
  const childrenOf = new Map<string, string[]>();
  const parentOf = new Map<string, string[]>();

  for (const edge of edges) {
    if (!childrenOf.has(edge.source)) childrenOf.set(edge.source, []);
    childrenOf.get(edge.source)!.push(edge.target);
    if (!parentOf.has(edge.target)) parentOf.set(edge.target, []);
    parentOf.get(edge.target)!.push(edge.source);
  }

  // Find root nodes (no parents)
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const roots = nodes.filter((n) => !parentOf.has(n.id) || parentOf.get(n.id)!.length === 0);

  // BFS to assign levels and positions
  const visited = new Set<string>();
  const levelNodes = new Map<number, string[]>();
  const queue: Array<{ id: string; level: number }> = [];

  for (const root of roots) {
    queue.push({ id: root.id, level: 0 });
  }

  while (queue.length > 0) {
    const { id, level } = queue.shift()!;
    if (visited.has(id)) continue;
    visited.add(id);

    if (!levelNodes.has(level)) levelNodes.set(level, []);
    levelNodes.get(level)!.push(id);

    const children = childrenOf.get(id) || [];
    for (const child of children) {
      if (!visited.has(child)) {
        queue.push({ id: child, level: level + 1 });
      }
    }
  }

  // Position nodes by level
  for (const [level, ids] of levelNodes.entries()) {
    const totalWidth = (ids.length - 1) * HORIZONTAL_SPACING;
    const startX = X_CENTER - totalWidth / 2;

    ids.forEach((id, idx) => {
      const node = nodeMap.get(id);
      if (node) {
        node.position = {
          x: startX + idx * HORIZONTAL_SPACING,
          y: level * VERTICAL_SPACING + 50,
        };
      }
    });
  }
}
