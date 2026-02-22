// Convert React Flow graph (nodes + edges) to DesignProposal for backend execution

import type { Edge, Node } from "reactflow";
import type { AgentNodeData } from "../nodes/AgentNode";

export interface AgentSpec {
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

export interface EdgeSpec {
  source: string;
  target: string;
  condition?: string;
}

export interface DesignProposal {
  name: string;
  description: string;
  agents: AgentSpec[];
  edges?: EdgeSpec[];
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
 * Check if graph has any parallel branches (fan-out from same source).
 */
function hasParallelBranches(edges: Edge[]): boolean {
  const sourceCounts = new Map<string, number>();
  for (const edge of edges) {
    sourceCounts.set(edge.source, (sourceCounts.get(edge.source) || 0) + 1);
  }
  return Array.from(sourceCounts.values()).some((count) => count > 1);
}

/**
 * Check if any edge has a condition.
 */
function hasConditionalEdges(edges: Edge[]): boolean {
  return edges.some(
    (e) => e.type === "conditional" && (e.data as { condition?: string })?.condition
  );
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

  // Build node id -> agent name map
  const idToName = new Map<string, string>();
  for (const node of sortedNodes) {
    idToName.set(node.id, node.data.name);
  }

  const agents: AgentSpec[] = sortedNodes.map((node) => {
    const spec: AgentSpec = {
      name: node.data.name,
      role: node.data.role,
      llm_model: node.data.llmModel,
      description: node.data.description || `${node.data.role} agent`,
    };
    // Include extended fields if present
    if (node.data.customPrompt) spec.custom_prompt = node.data.customPrompt;
    if (node.data.temperature !== undefined) spec.temperature = node.data.temperature;
    if (node.data.maxTokens !== undefined) spec.max_tokens = node.data.maxTokens;
    if (node.data.retryCount !== undefined) spec.retry_count = node.data.retryCount;
    if (node.data.isCustomRole) spec.is_custom_role = true;
    return spec;
  });

  const result: DesignProposal = {
    name: "Custom Pipeline",
    description: "Pipeline created from visual editor",
    agents,
    pros: [],
    cons: [],
    estimated_cost: "varies",
    complexity: agents.length <= 2 ? "low" : agents.length <= 4 ? "medium" : "high",
    recommended: false,
  };

  // Include explicit edges if graph has parallel branches or conditional edges
  if (hasParallelBranches(edges) || hasConditionalEdges(edges)) {
    result.edges = edges.map((e) => {
      const edgeSpec: EdgeSpec = {
        source: idToName.get(e.source) || e.source,
        target: idToName.get(e.target) || e.target,
      };
      if (e.type === "conditional" && (e.data as { condition?: string })?.condition) {
        edgeSpec.condition = (e.data as { condition: string }).condition;
      }
      return edgeSpec;
    });
  }

  return result;
}
