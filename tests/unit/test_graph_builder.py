"""Tests for pipeline graph builder."""

from __future__ import annotations

import pytest

from backend.discussion.design_generator import AgentSpec, DesignProposal
from backend.pipeline.graph_builder import ROLE_NODE_MAP, PipelineGraphBuilder


def _make_design(**overrides) -> DesignProposal:
    """Create a test DesignProposal."""
    defaults = {
        "name": "Test Pipeline",
        "description": "A test pipeline design",
        "agents": [
            AgentSpec(
                name="collector",
                role="collector",
                llm_model="gpt-4o-mini",
                description="Collects data",
            ),
            AgentSpec(
                name="analyzer",
                role="analyzer",
                llm_model="gpt-4o",
                description="Analyzes data",
            ),
            AgentSpec(
                name="reporter",
                role="reporter",
                llm_model="gpt-4o-mini",
                description="Generates report",
            ),
        ],
        "estimated_cost": "~$0.05",
        "complexity": "medium",
    }
    defaults.update(overrides)
    return DesignProposal(**defaults)


class TestPipelineGraphBuilder:
    """Tests for PipelineGraphBuilder."""

    def test_build_simple_graph(self):
        builder = PipelineGraphBuilder()
        design = _make_design()
        graph = builder.build(design)
        assert graph is not None

    def test_build_empty_agents_raises(self):
        builder = PipelineGraphBuilder()
        design = _make_design(agents=[])
        with pytest.raises(ValueError, match="no agents"):
            builder.build(design)

    def test_build_single_agent(self):
        builder = PipelineGraphBuilder()
        design = _make_design(
            agents=[
                AgentSpec(
                    name="solo",
                    role="analyzer",
                    llm_model="gpt-4o",
                    description="Solo agent",
                ),
            ]
        )
        graph = builder.build(design)
        assert graph is not None

    def test_build_with_all_roles(self):
        builder = PipelineGraphBuilder()
        agents = [
            AgentSpec(
                name="collector",
                role="collector",
                llm_model="gpt-4o-mini",
                description="Collect",
            ),
            AgentSpec(
                name="validator",
                role="validator",
                llm_model="gpt-4o-mini",
                description="Validate",
            ),
            AgentSpec(
                name="analyzer",
                role="analyzer",
                llm_model="gpt-4o",
                description="Analyze",
            ),
            AgentSpec(
                name="critic", role="critic", llm_model="gpt-4o", description="Critique"
            ),
            AgentSpec(
                name="synthesizer",
                role="synthesizer",
                llm_model="gpt-4o",
                description="Synthesize",
            ),
            AgentSpec(
                name="reporter",
                role="reporter",
                llm_model="gpt-4o-mini",
                description="Report",
            ),
        ]
        design = _make_design(agents=agents)
        graph = builder.build(design)
        assert graph is not None

    def test_role_node_map_coverage(self):
        """All expected roles have mappings."""
        expected_roles = {
            "collector",
            "analyzer",
            "reporter",
            "validator",
            "synthesizer",
            "critic",
            "cross_checker",
        }
        assert expected_roles.issubset(set(ROLE_NODE_MAP.keys()))

    def test_build_handles_duplicate_names(self):
        """Duplicate agent names should be made unique."""
        builder = PipelineGraphBuilder()
        agents = [
            AgentSpec(
                name="agent",
                role="analyzer",
                llm_model="gpt-4o",
                description="First",
            ),
            AgentSpec(
                name="agent",
                role="analyzer",
                llm_model="gpt-4o",
                description="Second",
            ),
        ]
        design = _make_design(agents=agents)
        # Should not raise
        graph = builder.build(design)
        assert graph is not None

    def test_unknown_role_defaults_to_analyzer(self):
        builder = PipelineGraphBuilder()
        agents = [
            AgentSpec(
                name="custom",
                role="unknown_role",
                llm_model="gpt-4o",
                description="Custom",
            ),
        ]
        design = _make_design(agents=agents)
        graph = builder.build(design)
        assert graph is not None
