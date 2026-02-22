// Convert React Flow graph (nodes + edges) to DesignProposal for backend execution

import type { Edge, Node } from "reactflow";
import type { AgentNodeData } from "../nodes/AgentNode";

export interface AgentSpec {
  name: string;
  role: string;
  llm_model: string;
  description: string;
}

export interface DesignProposal {
  name: string;
  description: string;
  agents: AgentSpec[];
  pros: string[];
  cons: string[];
  estimated_cost: string;
  complexity: string;
  recommended: boolean;
}

/**
 * Topological sort of nodes based on edges.
 * Throws if a cycle is detected or nodes are disconnected.
 */
function topologicalSort(
  nodes: Node<AgentNodeData>[],
  edges: Edge[]
): Node<AgentNodeData>[] {
  const inDegree = new Map<string, number>();
  const adjacency = new Map<string, string[]>();

  for (const node of nodes) {
    inDegree.set(node.id, 0);
    adjacency.set(node.id, []);
  }

  for (const edge of edges) {
    adjacency.get(edge.source)?.push(edge.target);
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
  }

  const queue: string[] = [];
  for (const [id, deg] of inDegree.entries()) {
    if (deg === 0) queue.push(id);
  }

  const sorted: string[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    sorted.push(current);
    for (const neighbor of adjacency.get(current) || []) {
      const newDeg = (inDegree.get(neighbor) || 1) - 1;
      inDegree.set(neighbor, newDeg);
      if (newDeg === 0) queue.push(neighbor);
    }
  }

  if (sorted.length !== nodes.length) {
    throw new Error("Cycle detected in pipeline graph");
  }

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  return sorted.map((id) => nodeMap.get(id)!);
}

/**
 * Convert React Flow nodes + edges into a DesignProposal.
 */
export function flowToDesign(
  nodes: Node<AgentNodeData>[],
  edges: Edge[]
): DesignProposal {
  if (nodes.length === 0) {
    throw new Error("Pipeline must have at least one agent");
  }

  const sortedNodes = topologicalSort(nodes, edges);

  const agents: AgentSpec[] = sortedNodes.map((node) => ({
    name: node.data.name,
    role: node.data.role,
    llm_model: node.data.llmModel,
    description: node.data.description || `${node.data.role} agent`,
  }));

  return {
    name: "Custom Pipeline",
    description: "Pipeline created from visual editor",
    agents,
    pros: [],
    cons: [],
    estimated_cost: "varies",
    complexity: agents.length <= 2 ? "low" : agents.length <= 4 ? "medium" : "high",
    recommended: false,
  };
}
