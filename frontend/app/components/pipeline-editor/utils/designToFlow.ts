// Convert DesignProposal to React Flow nodes + edges for visualization

import type { Edge, Node } from "reactflow";
import type { AgentNodeData } from "../nodes/AgentNode";

interface AgentSpec {
  name: string;
  role: string;
  llm_model: string;
  description: string;
}

interface DesignProposal {
  name: string;
  description: string;
  agents: AgentSpec[];
}

const VERTICAL_SPACING = 150;
const X_CENTER = 300;

/**
 * Convert a DesignProposal into React Flow nodes and edges.
 * Lays out nodes vertically in sequential order.
 */
export function designToFlow(design: DesignProposal): {
  nodes: Node<AgentNodeData>[];
  edges: Edge[];
} {
  const nodes: Node<AgentNodeData>[] = design.agents.map((agent, index) => ({
    id: `agent-${index + 1}`,
    type: "agentNode",
    position: {
      x: X_CENTER,
      y: index * VERTICAL_SPACING + 50,
    },
    data: {
      name: agent.name,
      role: agent.role,
      llmModel: agent.llm_model,
      description: agent.description,
      status: "idle" as const,
    },
  }));

  const edges: Edge[] = [];
  for (let i = 0; i < nodes.length - 1; i++) {
    edges.push({
      id: `edge-${nodes[i].id}-${nodes[i + 1].id}`,
      source: nodes[i].id,
      target: nodes[i + 1].id,
      animated: false,
    });
  }

  return { nodes, edges };
}
