"""Graph Builder - Converts DesignProposal to LangGraph StateGraph."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from backend.pipeline.agents.analyzer import AnalyzerNode
from backend.pipeline.agents.collector import CollectorNode
from backend.pipeline.agents.reporter import ReporterNode
from backend.pipeline.agents.synthesizer import SynthesizerNode
from backend.pipeline.agents.validator import ValidatorNode
from backend.pipeline.state import PipelineState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from backend.discussion.design_generator import AgentSpec, DesignProposal

logger = logging.getLogger(__name__)

MAX_AGENTS = 20

# Role -> Node class mapping
ROLE_NODE_MAP: dict[str, type] = {
    "collector": CollectorNode,
    "analyzer": AnalyzerNode,
    "reporter": ReporterNode,
    "validator": ValidatorNode,
    "synthesizer": SynthesizerNode,
    "critic": AnalyzerNode,  # critic reuses analyzer
    "cross_checker": AnalyzerNode,  # cross_checker reuses analyzer
}


def _should_continue(state: PipelineState) -> str:
    """Check if pipeline should continue or stop."""
    # Stop if too many errors
    if len(state.get("errors", [])) >= 3:
        return "end"
    # Stop if max steps exceeded
    if state.get("current_step", 0) >= state.get("max_steps", 50):
        return "end"
    # Stop if status indicates termination
    if state.get("status", "") in ("failed", "timeout", "completed"):
        return "end"
    return "continue"


class PipelineGraphBuilder:
    """Converts a DesignProposal into a compiled LangGraph StateGraph."""

    def build(self, design: DesignProposal) -> CompiledStateGraph:
        """Build a LangGraph from a DesignProposal.

        Creates a sequential graph where each agent node runs in order.
        Adds conditional edges to check for errors/timeout between nodes.
        """
        agents = design.agents
        if not agents:
            raise ValueError("DesignProposal has no agents defined")
        if len(agents) > MAX_AGENTS:
            raise ValueError(f"Too many agents ({len(agents)}), maximum is {MAX_AGENTS}")

        graph = StateGraph(PipelineState)
        node_names: list[str] = []

        name_counts: dict[str, int] = {}
        for agent_spec in agents:
            node = self._create_node(agent_spec)
            node_name = agent_spec.name
            # Ensure unique node names with counter
            if node_name in name_counts:
                name_counts[node_name] += 1
                node_name = f"{node_name}_{name_counts[node_name]}"
            else:
                name_counts[node_name] = 0
            graph.add_node(node_name, node.execute)
            node_names.append(node_name)

        if not node_names:
            raise ValueError("No valid agent nodes could be created")

        # Connect: START -> first node
        graph.add_edge(START, node_names[0])

        # Connect nodes sequentially with continuation checks
        for i in range(len(node_names) - 1):
            current = node_names[i]
            next_node = node_names[i + 1]
            # Add conditional edge: continue to next or end
            graph.add_conditional_edges(
                current,
                _should_continue,
                {"continue": next_node, "end": END},
            )

        # Last node -> END
        graph.add_edge(node_names[-1], END)

        logger.info(f"Built graph with {len(node_names)} nodes: {' -> '.join(node_names)}")
        return graph.compile()

    def _create_node(self, agent_spec: AgentSpec) -> object:
        """Create an agent node from an AgentSpec."""
        node_class = ROLE_NODE_MAP.get(agent_spec.role, AnalyzerNode)
        return node_class(
            name=agent_spec.name,
            role=agent_spec.role,
            description=agent_spec.description,
            llm_model=agent_spec.llm_model,
        )
