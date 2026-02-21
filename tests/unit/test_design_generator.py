"""Tests for Design Generator - Pipeline design proposal generation."""

import pytest

from backend.discussion.design_generator import (
    AgentSpec,
    DesignGenerator,
    DesignProposal,
)


class TestAgentSpec:
    """Test AgentSpec model validation."""

    def test_create_agent_spec(self):
        """Test creating an AgentSpec with all fields."""
        spec = AgentSpec(
            name="data_collector",
            role="collector",
            llm_model="gpt-4o-mini",
            description="Collects data from web sources",
        )
        assert spec.name == "data_collector"
        assert spec.role == "collector"
        assert spec.llm_model == "gpt-4o-mini"
        assert spec.description == "Collects data from web sources"

    def test_agent_spec_requires_all_fields(self):
        """Test that AgentSpec requires all fields."""
        with pytest.raises(Exception):
            AgentSpec(name="test")  # type: ignore[call-arg]

    def test_agent_spec_various_roles(self):
        """Test AgentSpec with various roles."""
        roles = [
            "collector",
            "analyzer",
            "reporter",
            "validator",
            "critic",
            "synthesizer",
        ]
        for role in roles:
            spec = AgentSpec(
                name=f"test_{role}",
                role=role,
                llm_model="gpt-4o-mini",
                description=f"Test {role} agent",
            )
            assert spec.role == role


class TestDesignProposal:
    """Test DesignProposal model validation."""

    def test_create_design_proposal(self):
        """Test creating a DesignProposal with all fields."""
        proposal = DesignProposal(
            name="Test Pipeline",
            description="A test pipeline design",
            agents=[
                AgentSpec(
                    name="agent1",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="Test agent",
                )
            ],
            pros=["Simple", "Fast"],
            cons=["Limited"],
            estimated_cost="~/usr/bin/zsh.05",
            complexity="medium",
            recommended=True,
        )
        assert proposal.name == "Test Pipeline"
        assert proposal.description == "A test pipeline design"
        assert len(proposal.agents) == 1
        assert proposal.pros == ["Simple", "Fast"]
        assert proposal.cons == ["Limited"]
        assert proposal.estimated_cost == "~/usr/bin/zsh.05"
        assert proposal.complexity == "medium"
        assert proposal.recommended is True

    def test_design_proposal_defaults(self):
        """Test DesignProposal default values."""
        proposal = DesignProposal(
            name="Minimal",
            description="Minimal design",
        )
        assert proposal.agents == []
        assert proposal.pros == []
        assert proposal.cons == []
        assert proposal.estimated_cost == "unknown"
        assert proposal.complexity == "medium"
        assert proposal.recommended is False

    def test_design_proposal_complexity_values(self):
        """Test DesignProposal accepts various complexity values."""
        for complexity in ("low", "medium", "high"):
            proposal = DesignProposal(
                name="Test",
                description="Test",
                complexity=complexity,
            )
            assert proposal.complexity == complexity


class TestDesignGeneratorFallback:
    """Test DesignGenerator fallback methods (no LLM needed)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = DesignGenerator(router=None)

    def test_fallback_returns_at_least_two_proposals(self):
        """Test that fallback generates at least 2 proposals."""
        designs = self.generator.generate_designs_fallback({"task": "custom"})
        assert len(designs) >= 2

    def test_fallback_simple_task_returns_two_proposals(self):
        """Test fallback with simple task returns exactly 2 proposals."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "simple"}
        )
        assert len(designs) == 2

    def test_fallback_standard_task_returns_three_proposals(self):
        """Test fallback with standard task returns 3 proposals."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "standard"}
        )
        assert len(designs) == 3

    def test_fallback_complex_task_returns_three_proposals(self):
        """Test fallback with complex task returns 3 proposals."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "complex"}
        )
        assert len(designs) == 3

    def test_fallback_proposals_have_required_fields(self):
        """Test that fallback proposals have all required fields."""
        designs = self.generator.generate_designs_fallback(
            {
                "task": "data_collection",
                "source_type": "web",
                "estimated_complexity": "standard",
            }
        )
        for design in designs:
            assert isinstance(design.name, str)
            assert len(design.name) > 0
            assert isinstance(design.description, str)
            assert len(design.description) > 0
            assert isinstance(design.agents, list)
            assert isinstance(design.pros, list)
            assert len(design.pros) > 0
            assert isinstance(design.cons, list)
            assert len(design.cons) > 0
            assert isinstance(design.estimated_cost, str)
            assert isinstance(design.complexity, str)
            assert isinstance(design.recommended, bool)

    def test_fallback_each_proposal_has_at_least_one_agent(self):
        """Test each fallback proposal has at least one agent."""
        designs = self.generator.generate_designs_fallback(
            {
                "task": "analysis",
                "source_type": "web",
                "estimated_complexity": "complex",
            }
        )
        for design in designs:
            assert len(design.agents) >= 1
            for agent in design.agents:
                assert isinstance(agent, AgentSpec)
                assert agent.name
                assert agent.role
                assert agent.llm_model
                assert agent.description

    def test_fallback_exactly_one_recommended_simple(self):
        """Test exactly one proposal recommended for simple complexity."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "simple"}
        )
        recommended = [d for d in designs if d.recommended]
        assert len(recommended) == 1

    def test_fallback_exactly_one_recommended_standard(self):
        """Test exactly one proposal recommended for standard complexity."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "standard"}
        )
        recommended = [d for d in designs if d.recommended]
        assert len(recommended) == 1

    def test_fallback_exactly_one_recommended_complex(self):
        """Test exactly one proposal recommended for complex complexity."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "complex"}
        )
        recommended = [d for d in designs if d.recommended]
        assert len(recommended) == 1

    def test_fallback_complexity_values(self):
        """Test that complexity is one of low, medium, high."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "complex"}
        )
        valid_complexities = {"low", "medium", "high"}
        for design in designs:
            assert design.complexity in valid_complexities

    def test_fallback_design_names_are_distinct(self):
        """Test that generated designs have distinct names."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "complex"}
        )
        names = [d.name for d in designs]
        assert len(names) == len(set(names))

    def test_fallback_with_source_type_adds_collector(self):
        """Test that specifying source_type adds a collector agent."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "source_type": "web", "estimated_complexity": "simple"}
        )
        for design in designs:
            roles = [a.role for a in design.agents]
            assert "collector" in roles

    def test_fallback_without_source_type_no_collector(self):
        """Test that no collector agent when source_type is none."""
        designs = self.generator.generate_designs_fallback(
            {
                "task": "analysis",
                "source_type": "none",
                "estimated_complexity": "simple",
            }
        )
        for design in designs:
            roles = [a.role for a in design.agents]
            assert "collector" not in roles

    def test_fallback_simple_design_is_low_complexity(self):
        """Test that the first design always has low complexity."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "complex"}
        )
        assert designs[0].complexity == "low"

    def test_fallback_standard_design_is_medium_complexity(self):
        """Test that the second design has medium complexity."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "standard"}
        )
        assert designs[1].complexity == "medium"

    def test_fallback_advanced_design_is_high_complexity(self):
        """Test that the third design has high complexity."""
        designs = self.generator.generate_designs_fallback(
            {"task": "analysis", "estimated_complexity": "complex"}
        )
        assert designs[2].complexity == "high"

    def test_fallback_empty_requirements(self):
        """Test fallback with empty requirements dict."""
        designs = self.generator.generate_designs_fallback({})
        assert len(designs) >= 2
        for design in designs:
            assert design.name
            assert len(design.agents) >= 1

    def test_fallback_standard_design_has_validator_with_source(self):
        """Test standard design includes validator agent when source is provided."""
        designs = self.generator.generate_designs_fallback(
            {
                "task": "analysis",
                "source_type": "api",
                "estimated_complexity": "standard",
            }
        )
        standard_design = designs[1]
        roles = [a.role for a in standard_design.agents]
        assert "validator" in roles

    def test_fallback_advanced_design_has_critic(self):
        """Test advanced design includes a critic/cross-checker agent."""
        designs = self.generator.generate_designs_fallback(
            {
                "task": "analysis",
                "source_type": "web",
                "estimated_complexity": "complex",
            }
        )
        advanced_design = designs[2]
        roles = [a.role for a in advanced_design.agents]
        assert "critic" in roles
