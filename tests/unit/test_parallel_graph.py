"""Tests for Phase 8B parallel graph building."""

import pytest

from backend.pipeline.extended_models import (
    EdgeSpec,
    ExtendedAgentSpec,
    ExtendedDesignProposal,
)
from backend.pipeline.graph_builder import PipelineGraphBuilder


def _make_agent(name: str, role: str = "analyzer") -> ExtendedAgentSpec:
    """Helper to create an ExtendedAgentSpec."""
    return ExtendedAgentSpec(
        name=name,
        role=role,
        llm_model="gpt-4o-mini",
        description=f"{name} agent",
    )


class TestParallelGraphBuild:
    """Tests for parallel graph building."""

    def test_sequential_without_edges(self):
        """Graph without edges field builds sequentially."""
        design = ExtendedDesignProposal(
            name="seq",
            description="sequential",
            agents=[_make_agent("a"), _make_agent("b"), _make_agent("c")],
        )
        builder = PipelineGraphBuilder()
        graph = builder.build(design)
        assert graph is not None

    def test_explicit_sequential_edges(self):
        """Graph with explicit sequential edges builds correctly."""
        design = ExtendedDesignProposal(
            name="seq",
            description="sequential",
            agents=[_make_agent("a"), _make_agent("b"), _make_agent("c")],
            edges=[
                EdgeSpec(source="a", target="b"),
                EdgeSpec(source="b", target="c"),
            ],
        )
        builder = PipelineGraphBuilder()
        graph = builder.build(design)
        assert graph is not None

    def test_fan_out(self):
        """Graph with fan-out (one source, multiple targets) builds."""
        design = ExtendedDesignProposal(
            name="parallel",
            description="parallel pipeline",
            agents=[
                _make_agent("start"),
                _make_agent("branch_a"),
                _make_agent("branch_b"),
            ],
            edges=[
                EdgeSpec(source="start", target="branch_a"),
                EdgeSpec(source="start", target="branch_b"),
            ],
        )
        builder = PipelineGraphBuilder()
        graph = builder.build(design)
        assert graph is not None

    def test_fan_out_fan_in(self):
        """Graph with fan-out and fan-in builds."""
        design = ExtendedDesignProposal(
            name="diamond",
            description="diamond pipeline",
            agents=[
                _make_agent("start"),
                _make_agent("left"),
                _make_agent("right"),
                _make_agent("merge", "synthesizer"),
            ],
            edges=[
                EdgeSpec(source="start", target="left"),
                EdgeSpec(source="start", target="right"),
                EdgeSpec(source="left", target="merge"),
                EdgeSpec(source="right", target="merge"),
            ],
        )
        builder = PipelineGraphBuilder()
        graph = builder.build(design)
        assert graph is not None

    def test_invalid_source_raises(self):
        """Edge with nonexistent source raises ValueError."""
        design = ExtendedDesignProposal(
            name="bad",
            description="bad edges",
            agents=[_make_agent("a")],
            edges=[EdgeSpec(source="nonexistent", target="a")],
        )
        builder = PipelineGraphBuilder()
        with pytest.raises(ValueError, match="not found"):
            builder.build(design)

    def test_invalid_target_raises(self):
        """Edge with nonexistent target raises ValueError."""
        design = ExtendedDesignProposal(
            name="bad",
            description="bad edges",
            agents=[_make_agent("a")],
            edges=[EdgeSpec(source="a", target="nonexistent")],
        )
        builder = PipelineGraphBuilder()
        with pytest.raises(ValueError, match="not found"):
            builder.build(design)

    def test_no_agents_raises(self):
        """Empty agents list raises ValueError."""
        design = ExtendedDesignProposal(
            name="empty", description="no agents", agents=[]
        )
        builder = PipelineGraphBuilder()
        with pytest.raises(ValueError, match="no agents"):
            builder.build(design)

    def test_too_many_agents_raises(self):
        """More than MAX_AGENTS raises ValueError."""
        agents = [_make_agent(f"agent_{i}") for i in range(21)]
        design = ExtendedDesignProposal(
            name="big", description="too many", agents=agents
        )
        builder = PipelineGraphBuilder()
        with pytest.raises(ValueError, match="Too many"):
            builder.build(design)

    def test_custom_agent_node_created(self):
        """Custom role agent uses CustomAgentNode."""
        design = ExtendedDesignProposal(
            name="custom",
            description="custom role",
            agents=[
                ExtendedAgentSpec(
                    name="my_agent",
                    role="summarizer",
                    llm_model="gpt-4o",
                    description="custom agent",
                    is_custom_role=True,
                    custom_prompt="You summarize things.",
                )
            ],
        )
        builder = PipelineGraphBuilder()
        graph = builder.build(design)
        assert graph is not None

    def test_partial_cycle_raises(self):
        """Partial cycle (A->B, B->C, C->B) is detected."""
        design = ExtendedDesignProposal(
            name="cycle",
            description="partial cycle",
            agents=[_make_agent("a"), _make_agent("b"), _make_agent("c")],
            edges=[
                EdgeSpec(source="a", target="b"),
                EdgeSpec(source="b", target="c"),
                EdgeSpec(source="c", target="b"),
            ],
        )
        builder = PipelineGraphBuilder()
        with pytest.raises(ValueError, match="Cycle detected"):
            builder.build(design)

    def test_extended_params_passed(self):
        """Extended parameters (temperature, max_tokens, retry_count) are passed."""
        agent = ExtendedAgentSpec(
            name="test",
            role="analyzer",
            llm_model="gpt-4o",
            description="test",
            temperature=1.5,
            max_tokens=8192,
            retry_count=5,
        )
        builder = PipelineGraphBuilder()
        node = builder._create_node(agent)
        assert node.temperature == 1.5
        assert node.max_tokens == 8192
        assert node.retry_count == 5
