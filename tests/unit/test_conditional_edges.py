"""Tests for Phase 8B conditional edge parsing and evaluation."""

import pytest

from backend.pipeline.extended_models import (
    EdgeSpec,
    ExtendedAgentSpec,
    ExtendedDesignProposal,
)
from backend.pipeline.graph_builder import (
    PipelineGraphBuilder,
    extract_field,
    make_condition_fn,
    parse_condition,
)


class TestParseCondition:
    """Tests for parse_condition function."""

    def test_greater_than(self):
        """Parse 'score > 0.8'."""
        field, op, value = parse_condition("score > 0.8")
        assert field == "score"
        assert op == ">"
        assert value == "0.8"

    def test_less_than(self):
        """Parse 'cost < 100'."""
        field, op, value = parse_condition("cost < 100")
        assert field == "cost"
        assert op == "<"
        assert value == "100"

    def test_greater_equal(self):
        """Parse 'count >= 5'."""
        field, op, value = parse_condition("count >= 5")
        assert field == "count"
        assert op == ">="
        assert value == "5"

    def test_less_equal(self):
        """Parse 'age <= 30'."""
        field, op, value = parse_condition("age <= 30")
        assert field == "age"
        assert op == "<="
        assert value == "30"

    def test_equal(self):
        """Parse 'status == 1'."""
        field, op, value = parse_condition("status == 1")
        assert field == "status"
        assert op == "=="
        assert value == "1"

    def test_negative_value(self):
        """Parse 'score > -0.5'."""
        field, op, value = parse_condition("score > -0.5")
        assert field == "score"
        assert op == ">"
        assert value == "-0.5"

    def test_invalid_format_raises(self):
        """Invalid condition format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid condition"):
            parse_condition("not a condition")

    def test_invalid_operator_raises(self):
        """Unsupported operator raises ValueError."""
        with pytest.raises(ValueError, match="Invalid condition"):
            parse_condition("score != 5")

    def test_code_injection_rejected(self):
        """Code injection attempts are rejected."""
        with pytest.raises(ValueError, match="Invalid condition"):
            parse_condition("__import__('os').system('rm -rf /')")

    def test_whitespace_handling(self):
        """Extra whitespace is handled."""
        field, op, value = parse_condition("  score  >  0.8  ")
        assert field == "score"
        assert op == ">"
        assert value == "0.8"


class TestExtractField:
    """Tests for extract_field function."""

    def test_top_level_field(self):
        """Extract a top-level state field."""
        state = {
            "cost_total": 1.5,
            "current_step": 3,
            "agent_results": [],
            "errors": [],
        }
        assert extract_field(state, "cost_total") == 1.5

    def test_last_result_field(self):
        """Extract field from last agent result."""
        state = {
            "agent_results": [{"agent_name": "a", "score": 0.9}],
            "errors": [],
            "current_step": 1,
        }
        assert extract_field(state, "score") == 0.9

    def test_missing_field_returns_zero(self):
        """Missing field returns 0.0."""
        state = {"agent_results": [], "errors": [], "current_step": 0}
        assert extract_field(state, "nonexistent") == 0.0


class TestMakeConditionFn:
    """Tests for make_condition_fn function."""

    def test_true_condition(self):
        """Condition evaluates to true."""
        fn = make_condition_fn("cost_total > 1.0")
        state = {
            "cost_total": 2.0,
            "agent_results": [],
            "errors": [],
            "current_step": 0,
        }
        assert fn(state) is True

    def test_false_condition(self):
        """Condition evaluates to false."""
        fn = make_condition_fn("cost_total > 5.0")
        state = {
            "cost_total": 2.0,
            "agent_results": [],
            "errors": [],
            "current_step": 0,
        }
        assert fn(state) is False

    def test_equal_condition(self):
        """Equality condition."""
        fn = make_condition_fn("current_step == 3")
        state = {"current_step": 3, "agent_results": [], "errors": []}
        assert fn(state) is True


class TestConditionalGraphBuild:
    """Tests for building graphs with conditional edges."""

    def _make_agent(self, name: str) -> ExtendedAgentSpec:
        return ExtendedAgentSpec(
            name=name,
            role="analyzer",
            llm_model="gpt-4o-mini",
            description=f"{name} agent",
        )

    def test_conditional_edge_builds(self):
        """Graph with conditional edges compiles successfully."""
        design = ExtendedDesignProposal(
            name="conditional",
            description="conditional pipeline",
            agents=[
                self._make_agent("start"),
                self._make_agent("high_path"),
                self._make_agent("low_path"),
            ],
            edges=[
                EdgeSpec(
                    source="start", target="high_path", condition="cost_total > 0.5"
                ),
                EdgeSpec(source="start", target="low_path"),
            ],
        )
        builder = PipelineGraphBuilder()
        graph = builder.build(design)
        assert graph is not None

    def test_invalid_condition_raises(self):
        """Invalid condition in edge raises ValueError."""
        design = ExtendedDesignProposal(
            name="bad",
            description="bad condition",
            agents=[self._make_agent("a"), self._make_agent("b")],
            edges=[
                EdgeSpec(source="a", target="b", condition="INVALID CONDITION"),
            ],
        )
        builder = PipelineGraphBuilder()
        with pytest.raises(ValueError, match="Invalid condition"):
            builder.build(design)

    def test_all_conditional_edges(self):
        """Graph where all edges from a source are conditional."""
        design = ExtendedDesignProposal(
            name="all_cond",
            description="all conditional",
            agents=[
                self._make_agent("start"),
                self._make_agent("path_a"),
                self._make_agent("path_b"),
            ],
            edges=[
                EdgeSpec(source="start", target="path_a", condition="cost_total > 1.0"),
                EdgeSpec(
                    source="start", target="path_b", condition="cost_total <= 1.0"
                ),
            ],
        )
        builder = PipelineGraphBuilder()
        graph = builder.build(design)
        assert graph is not None
