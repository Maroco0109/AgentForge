"""Graph Builder - Converts DesignProposal to LangGraph StateGraph."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from operator import eq, ge, gt, le, lt
from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from backend.pipeline.agents.analyzer import AnalyzerNode
from backend.pipeline.agents.collector import CollectorNode
from backend.pipeline.agents.custom import CustomAgentNode
from backend.pipeline.agents.reporter import ReporterNode
from backend.pipeline.agents.synthesizer import SynthesizerNode
from backend.pipeline.agents.validator import ValidatorNode
from backend.pipeline.state import PipelineState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from backend.discussion.design_generator import AgentSpec, DesignProposal
    from backend.pipeline.extended_models import ExtendedAgentSpec, ExtendedDesignProposal

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

# Safe comparison operators for conditional edges
SAFE_OPS = {">": gt, "<": lt, ">=": ge, "<=": le, "==": eq}

_CONDITION_RE = re.compile(r"^(\w+)\s*(>=|<=|==|>|<)\s*(-?\d+(?:\.\d+)?)$")


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


def parse_condition(condition_str: str) -> tuple[str, str, str]:
    """Parse a condition string of the form 'field op value'.

    Only allows safe numeric comparisons. No eval/exec.
    """
    match = _CONDITION_RE.match(condition_str.strip())
    if not match:
        raise ValueError(
            f"Invalid condition format: '{condition_str}'. "
            "Expected 'field op value' (e.g. 'score > 0.8')"
        )
    return match.group(1), match.group(2), match.group(3)


def extract_field(state: PipelineState, field: str) -> float:
    """Extract a numeric field from pipeline state for condition evaluation."""
    # Check top-level state fields
    if field in state:
        val = state[field]
        try:
            return float(val)
        except (TypeError, ValueError):
            pass

    # Check last agent result
    results = state.get("agent_results", [])
    if results:
        last_result = results[-1]
        if isinstance(last_result, dict) and field in last_result:
            try:
                return float(last_result[field])
            except (TypeError, ValueError):
                pass

    return 0.0


def make_condition_fn(condition_str: str):
    """Create a safe condition evaluation function. No eval/exec."""
    field, op_str, value = parse_condition(condition_str)
    op_fn = SAFE_OPS[op_str]
    threshold = float(value)

    def _evaluate(state: PipelineState) -> bool:
        return op_fn(extract_field(state, field), threshold)

    return _evaluate


class PipelineGraphBuilder:
    """Converts a DesignProposal into a compiled LangGraph StateGraph."""

    def build(self, design: DesignProposal | ExtendedDesignProposal) -> CompiledStateGraph:
        """Build a LangGraph from a DesignProposal.

        Supports both sequential (legacy) and explicit edge topology (Phase 8B).
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

        # Check if this is an ExtendedDesignProposal with explicit edges
        edges = getattr(design, "edges", None)
        if edges:
            self._build_explicit_topology(graph, node_names, edges)
        else:
            self._build_sequential_topology(graph, node_names)

        logger.info(f"Built graph with {len(node_names)} nodes: {', '.join(node_names)}")
        return graph.compile()

    def _build_sequential_topology(self, graph: StateGraph, node_names: list[str]) -> None:
        """Build sequential graph: START -> A -> B -> C -> END."""
        graph.add_edge(START, node_names[0])

        for i in range(len(node_names) - 1):
            current = node_names[i]
            next_node = node_names[i + 1]
            graph.add_conditional_edges(
                current,
                _should_continue,
                {"continue": next_node, "end": END},
            )

        graph.add_edge(node_names[-1], END)

    def _build_explicit_topology(self, graph: StateGraph, node_names: list[str], edges) -> None:
        """Build graph from explicit edge specs with parallel/conditional support."""
        node_set = set(node_names)

        # Group edges by source
        outgoing: dict[str, list] = defaultdict(list)
        targets_with_incoming: set[str] = set()
        sources: set[str] = set()

        for edge in edges:
            if edge.source not in node_set:
                raise ValueError(f"Edge source '{edge.source}' not found in agents")
            if edge.target not in node_set:
                raise ValueError(f"Edge target '{edge.target}' not found in agents")
            outgoing[edge.source].append(edge)
            targets_with_incoming.add(edge.target)
            sources.add(edge.source)

        # Find entry nodes (no incoming edges)
        entry_nodes = [n for n in node_names if n not in targets_with_incoming]
        if not entry_nodes:
            raise ValueError("No entry nodes found (cycle in edge topology)")

        # Connect START to entry nodes
        if len(entry_nodes) == 1:
            graph.add_edge(START, entry_nodes[0])
        else:
            # Multiple entry nodes -> fan-out from START
            def _start_fan_out(state: PipelineState):
                return [Send(n, state) for n in entry_nodes]

            graph.add_conditional_edges(START, _start_fan_out)

        # Process each source node's outgoing edges
        for source in node_names:
            source_edges = outgoing.get(source, [])
            if not source_edges:
                # Terminal node -> END
                graph.add_edge(source, END)
                continue

            # Check for conditional edges
            conditional_edges = [e for e in source_edges if e.condition]
            unconditional_edges = [e for e in source_edges if not e.condition]

            if conditional_edges and unconditional_edges:
                # Mix of conditional and unconditional -> use conditional routing
                self._add_conditional_routing(graph, source, source_edges)
            elif conditional_edges:
                # All conditional
                self._add_conditional_routing(graph, source, conditional_edges)
            elif len(unconditional_edges) == 1:
                # Single unconditional edge with continuation check
                graph.add_conditional_edges(
                    source,
                    _should_continue,
                    {"continue": unconditional_edges[0].target, "end": END},
                )
            else:
                # Multiple unconditional edges -> fan-out (parallel)
                targets = [e.target for e in unconditional_edges]
                self._add_fan_out(graph, source, targets)

    def _add_fan_out(self, graph: StateGraph, source: str, targets: list[str]) -> None:
        """Add fan-out edges from source to multiple targets using Send()."""

        def _route(state: PipelineState):
            if _should_continue(state) == "end":
                return []
            return [Send(t, state) for t in targets]

        graph.add_conditional_edges(source, _route)

    def _add_conditional_routing(self, graph: StateGraph, source: str, edges) -> None:
        """Add conditional routing from source based on edge conditions."""
        # Build condition functions for each edge
        condition_pairs: list[tuple] = []
        default_target: str | None = None

        for edge in edges:
            if edge.condition:
                condition_pairs.append((make_condition_fn(edge.condition), edge.target))
            else:
                default_target = edge.target

        def _conditional_route(state: PipelineState):
            if _should_continue(state) == "end":
                return []
            targets = []
            for cond_fn, target in condition_pairs:
                if cond_fn(state):
                    targets.append(Send(target, state))
            if not targets and default_target:
                targets.append(Send(default_target, state))
            if not targets:
                # No condition matched and no default -> end
                return []
            return targets

        graph.add_conditional_edges(source, _conditional_route)

    def _create_node(self, agent_spec: AgentSpec | ExtendedAgentSpec) -> object:
        """Create an agent node from an AgentSpec or ExtendedAgentSpec."""
        from backend.pipeline.extended_models import ExtendedAgentSpec

        if isinstance(agent_spec, ExtendedAgentSpec):
            if agent_spec.is_custom_role:
                cls = CustomAgentNode
            else:
                cls = ROLE_NODE_MAP.get(agent_spec.role, AnalyzerNode)
            return cls(
                name=agent_spec.name,
                role=agent_spec.role,
                description=agent_spec.description,
                llm_model=agent_spec.llm_model,
                temperature=agent_spec.temperature,
                max_tokens=agent_spec.max_tokens,
                retry_count=agent_spec.retry_count,
                **(
                    {"custom_prompt": agent_spec.custom_prompt} if agent_spec.is_custom_role else {}
                ),
            )

        # Legacy AgentSpec compatibility
        node_class = ROLE_NODE_MAP.get(agent_spec.role, AnalyzerNode)
        return node_class(
            name=agent_spec.name,
            role=agent_spec.role,
            description=agent_spec.description,
            llm_model=agent_spec.llm_model,
        )
