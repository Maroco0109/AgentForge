"""Tests for Phase 8B extended models."""

import pytest
from pydantic import ValidationError

from backend.pipeline.extended_models import (
    EdgeSpec,
    ExtendedAgentSpec,
    ExtendedDesignProposal,
)


class TestExtendedAgentSpec:
    """Tests for ExtendedAgentSpec model."""

    def test_defaults(self):
        """Default values are set correctly."""
        spec = ExtendedAgentSpec(
            name="test", role="analyzer", llm_model="gpt-4o", description="test agent"
        )
        assert spec.temperature == 0.7
        assert spec.max_tokens == 4096
        assert spec.retry_count == 3
        assert spec.custom_prompt is None
        assert spec.is_custom_role is False

    def test_custom_values(self):
        """Custom values are accepted."""
        spec = ExtendedAgentSpec(
            name="test",
            role="custom_role",
            llm_model="gpt-4o",
            description="test",
            temperature=1.5,
            max_tokens=8192,
            retry_count=5,
            custom_prompt="You are a helpful assistant.",
            is_custom_role=True,
        )
        assert spec.temperature == 1.5
        assert spec.max_tokens == 8192
        assert spec.retry_count == 5
        assert spec.custom_prompt == "You are a helpful assistant."
        assert spec.is_custom_role is True

    def test_inherits_agent_spec(self):
        """ExtendedAgentSpec inherits from AgentSpec."""
        spec = ExtendedAgentSpec(
            name="test", role="analyzer", llm_model="gpt-4o", description="test"
        )
        assert spec.name == "test"
        assert spec.role == "analyzer"
        assert spec.llm_model == "gpt-4o"

    def test_temperature_min(self):
        """Temperature below 0.0 is rejected."""
        with pytest.raises(ValidationError, match="temperature"):
            ExtendedAgentSpec(
                name="t", role="r", llm_model="m", description="d", temperature=-0.1
            )

    def test_temperature_max(self):
        """Temperature above 2.0 is rejected."""
        with pytest.raises(ValidationError, match="temperature"):
            ExtendedAgentSpec(
                name="t", role="r", llm_model="m", description="d", temperature=2.1
            )

    def test_temperature_boundary_min(self):
        """Temperature 0.0 is accepted."""
        spec = ExtendedAgentSpec(
            name="t", role="r", llm_model="m", description="d", temperature=0.0
        )
        assert spec.temperature == 0.0

    def test_temperature_boundary_max(self):
        """Temperature 2.0 is accepted."""
        spec = ExtendedAgentSpec(
            name="t", role="r", llm_model="m", description="d", temperature=2.0
        )
        assert spec.temperature == 2.0

    def test_max_tokens_min(self):
        """max_tokens below 1 is rejected."""
        with pytest.raises(ValidationError, match="max_tokens"):
            ExtendedAgentSpec(
                name="t", role="r", llm_model="m", description="d", max_tokens=0
            )

    def test_max_tokens_max(self):
        """max_tokens above 16384 is rejected."""
        with pytest.raises(ValidationError, match="max_tokens"):
            ExtendedAgentSpec(
                name="t", role="r", llm_model="m", description="d", max_tokens=16385
            )

    def test_max_tokens_boundary(self):
        """max_tokens 1 and 16384 are accepted."""
        spec1 = ExtendedAgentSpec(
            name="t", role="r", llm_model="m", description="d", max_tokens=1
        )
        assert spec1.max_tokens == 1
        spec2 = ExtendedAgentSpec(
            name="t", role="r", llm_model="m", description="d", max_tokens=16384
        )
        assert spec2.max_tokens == 16384

    def test_retry_count_min(self):
        """retry_count below 0 is rejected."""
        with pytest.raises(ValidationError, match="retry_count"):
            ExtendedAgentSpec(
                name="t", role="r", llm_model="m", description="d", retry_count=-1
            )

    def test_retry_count_max(self):
        """retry_count above 10 is rejected."""
        with pytest.raises(ValidationError, match="retry_count"):
            ExtendedAgentSpec(
                name="t", role="r", llm_model="m", description="d", retry_count=11
            )

    def test_retry_count_boundary(self):
        """retry_count 0 and 10 are accepted."""
        spec1 = ExtendedAgentSpec(
            name="t", role="r", llm_model="m", description="d", retry_count=0
        )
        assert spec1.retry_count == 0
        spec2 = ExtendedAgentSpec(
            name="t", role="r", llm_model="m", description="d", retry_count=10
        )
        assert spec2.retry_count == 10


class TestEdgeSpec:
    """Tests for EdgeSpec model."""

    def test_basic(self):
        """Basic edge without condition."""
        edge = EdgeSpec(source="a", target="b")
        assert edge.source == "a"
        assert edge.target == "b"
        assert edge.condition is None

    def test_with_condition(self):
        """Edge with condition."""
        edge = EdgeSpec(source="a", target="b", condition="score > 0.8")
        assert edge.condition == "score > 0.8"


class TestExtendedDesignProposal:
    """Tests for ExtendedDesignProposal model."""

    def test_defaults(self):
        """Default edges is None (sequential execution)."""
        proposal = ExtendedDesignProposal(
            name="test",
            description="test proposal",
            agents=[
                ExtendedAgentSpec(
                    name="a1", role="analyzer", llm_model="gpt-4o", description="test"
                )
            ],
        )
        assert proposal.edges is None
        assert len(proposal.agents) == 1

    def test_with_edges(self):
        """Proposal with explicit edges."""
        proposal = ExtendedDesignProposal(
            name="test",
            description="test",
            agents=[
                ExtendedAgentSpec(
                    name="a1", role="analyzer", llm_model="gpt-4o", description="d"
                ),
                ExtendedAgentSpec(
                    name="a2", role="reporter", llm_model="gpt-4o-mini", description="d"
                ),
            ],
            edges=[EdgeSpec(source="a1", target="a2")],
        )
        assert len(proposal.edges) == 1
        assert proposal.edges[0].source == "a1"

    def test_inherits_design_proposal(self):
        """ExtendedDesignProposal inherits from DesignProposal."""
        proposal = ExtendedDesignProposal(
            name="test",
            description="test",
            agents=[],
            pros=["fast"],
            cons=["expensive"],
            estimated_cost="$0.10",
            complexity="high",
            recommended=True,
        )
        assert proposal.pros == ["fast"]
        assert proposal.recommended is True
