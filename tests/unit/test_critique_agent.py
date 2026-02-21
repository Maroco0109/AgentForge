"""Tests for Critique Agent - Design proposal analysis and evaluation."""

from backend.discussion.critique_agent import CritiqueAgent, CritiqueResult
from backend.discussion.design_generator import AgentSpec, DesignProposal


class TestCritiqueResult:
    """Test CritiqueResult model validation."""

    def test_create_critique_result(self):
        """Test creating a CritiqueResult with all fields."""
        result = CritiqueResult(
            design_name="Test Design",
            weaknesses=["No validation"],
            risks=["Data loss"],
            edge_cases=["Empty input"],
            security_concerns=["Unsanitized data"],
            cost_concerns=["Expensive models"],
            scalability_notes=["Can parallelize"],
            overall_score=0.75,
            recommendation="Solid choice",
        )
        assert result.design_name == "Test Design"
        assert result.weaknesses == ["No validation"]
        assert result.risks == ["Data loss"]
        assert result.edge_cases == ["Empty input"]
        assert result.security_concerns == ["Unsanitized data"]
        assert result.cost_concerns == ["Expensive models"]
        assert result.scalability_notes == ["Can parallelize"]
        assert result.overall_score == 0.75
        assert result.recommendation == "Solid choice"

    def test_critique_result_defaults(self):
        """Test CritiqueResult default values."""
        result = CritiqueResult(design_name="Test")
        assert result.weaknesses == []
        assert result.risks == []
        assert result.edge_cases == []
        assert result.security_concerns == []
        assert result.cost_concerns == []
        assert result.scalability_notes == []
        assert result.overall_score == 0.5
        assert result.recommendation == ""

    def test_critique_result_score_range(self):
        """Test CritiqueResult accepts scores in valid range."""
        low = CritiqueResult(design_name="Low", overall_score=0.0)
        assert low.overall_score == 0.0
        high = CritiqueResult(design_name="High", overall_score=1.0)
        assert high.overall_score == 1.0
        mid = CritiqueResult(design_name="Mid", overall_score=0.5)
        assert mid.overall_score == 0.5


def _make_design(
    name="Test Design",
    agents=None,
    complexity="medium",
    recommended=False,
):
    """Helper to create a DesignProposal for testing."""
    if agents is None:
        agents = [
            AgentSpec(
                name="processor",
                role="analyzer",
                llm_model="gpt-4o-mini",
                description="Processes data",
            ),
            AgentSpec(
                name="formatter",
                role="reporter",
                llm_model="gpt-4o-mini",
                description="Formats output",
            ),
        ]
    return DesignProposal(
        name=name,
        description=f"A {complexity} pipeline design",
        agents=agents,
        pros=["Pro 1"],
        cons=["Con 1"],
        estimated_cost="~/usr/bin/zsh.05",
        complexity=complexity,
        recommended=recommended,
    )


class TestCritiqueAgentFallback:
    """Test CritiqueAgent fallback methods (no LLM needed)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.agent = CritiqueAgent(router=None)

    def test_fallback_returns_results_for_each_design(self):
        """Test that fallback returns one result per design."""
        designs = [
            _make_design("Design A"),
            _make_design("Design B"),
            _make_design("Design C"),
        ]
        results = self.agent.critique_designs_fallback(designs, {})
        assert len(results) == 3
        assert results[0].design_name == "Design A"
        assert results[1].design_name == "Design B"
        assert results[2].design_name == "Design C"

    def test_fallback_scores_between_zero_and_one(self):
        """Test that all critique scores are between 0.0 and 1.0."""
        designs = [
            _make_design("Simple", complexity="low"),
            _make_design("Standard", complexity="medium"),
            _make_design("Advanced", complexity="high"),
        ]
        results = self.agent.critique_designs_fallback(designs, {})
        for result in results:
            assert 0.0 <= result.overall_score <= 1.0

    def test_fallback_identifies_weaknesses(self):
        """Test that fallback identifies weaknesses for designs without validation."""
        design = _make_design(
            "No Validator",
            agents=[
                AgentSpec(
                    name="processor",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="Processes data",
                ),
                AgentSpec(
                    name="formatter",
                    role="reporter",
                    llm_model="gpt-4o-mini",
                    description="Formats output",
                ),
            ],
        )
        results = self.agent.critique_designs_fallback([design], {})
        assert len(results) == 1
        weaknesses_text = " ".join(results[0].weaknesses)
        assert "validation" in weaknesses_text.lower()

    def test_fallback_has_recommendation_string(self):
        """Test that each critique has a non-empty recommendation string."""
        designs = [
            _make_design("Design A"),
            _make_design("Design B"),
        ]
        results = self.agent.critique_designs_fallback(designs, {})
        for result in results:
            assert isinstance(result.recommendation, str)
            assert len(result.recommendation) > 0

    def test_fallback_detects_few_agents_weakness(self):
        """Test that designs with very few agents get a weakness."""
        design = _make_design(
            "Solo Agent",
            agents=[
                AgentSpec(
                    name="solo",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="Does everything",
                )
            ],
        )
        results = self.agent.critique_designs_fallback([design], {})
        weaknesses_text = " ".join(results[0].weaknesses)
        assert "few agents" in weaknesses_text.lower()

    def test_fallback_detects_many_agents_weakness(self):
        """Test that designs with many agents get coordination weakness."""
        agents = [
            AgentSpec(
                name=f"agent_{i}",
                role="analyzer",
                llm_model="gpt-4o-mini",
                description=f"Agent {i}",
            )
            for i in range(6)
        ]
        design = _make_design("Many Agents", agents=agents)
        results = self.agent.critique_designs_fallback([design], {})
        weaknesses_text = " ".join(results[0].weaknesses)
        assert (
            "coordination" in weaknesses_text.lower()
            or "overhead" in weaknesses_text.lower()
        )

    def test_fallback_detects_expensive_models(self):
        """Test that designs with multiple expensive models get cost concern."""
        agents = [
            AgentSpec(
                name="a1", role="analyzer", llm_model="gpt-4o", description="Agent 1"
            ),
            AgentSpec(
                name="a2", role="critic", llm_model="gpt-4o", description="Agent 2"
            ),
            AgentSpec(
                name="a3", role="synthesizer", llm_model="gpt-4o", description="Agent 3"
            ),
        ]
        design = _make_design("Expensive", agents=agents)
        results = self.agent.critique_designs_fallback([design], {})
        cost_text = " ".join(results[0].cost_concerns)
        assert "expensive" in cost_text.lower()

    def test_fallback_security_concern_for_collector(self):
        """Test that designs with collector agent get security concern."""
        agents = [
            AgentSpec(
                name="collector",
                role="collector",
                llm_model="gpt-4o-mini",
                description="Collects data",
            ),
            AgentSpec(
                name="analyzer",
                role="analyzer",
                llm_model="gpt-4o-mini",
                description="Analyzes data",
            ),
        ]
        design = _make_design("With Collector", agents=agents)
        results = self.agent.critique_designs_fallback([design], {})
        assert len(results[0].security_concerns) > 0

    def test_fallback_complexity_mismatch_over_engineered(self):
        """Test score penalty for over-engineered design."""
        design = _make_design("Over-engineered", complexity="high")
        results = self.agent.critique_designs_fallback(
            [design], {"estimated_complexity": "simple"}
        )
        weaknesses_text = " ".join(results[0].weaknesses)
        assert "over-engineered" in weaknesses_text.lower()

    def test_fallback_complexity_mismatch_under_engineered(self):
        """Test score penalty for under-engineered design."""
        design = _make_design("Too Simple", complexity="low")
        results = self.agent.critique_designs_fallback(
            [design], {"estimated_complexity": "complex"}
        )
        weaknesses_text = " ".join(results[0].weaknesses)
        assert (
            "simple" in weaknesses_text.lower()
            or "complexity" in weaknesses_text.lower()
        )

    def test_fallback_edge_cases_always_present(self):
        """Test that edge cases list is always non-empty."""
        design = _make_design("Basic")
        results = self.agent.critique_designs_fallback([design], {})
        assert len(results[0].edge_cases) > 0

    def test_fallback_llm_rate_limit_edge_case(self):
        """Test that LLM API rate limits is always flagged as edge case."""
        design = _make_design("Basic")
        results = self.agent.critique_designs_fallback([design], {})
        edge_text = " ".join(results[0].edge_cases)
        assert "rate limit" in edge_text.lower() or "outage" in edge_text.lower()

    def test_fallback_score_clamped_minimum(self):
        """Test that score is clamped to minimum 0.1."""
        design = _make_design(
            "Bad Design",
            agents=[
                AgentSpec(
                    name="solo",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="Solo",
                )
            ],
            complexity="high",
        )
        results = self.agent.critique_designs_fallback(
            [design], {"estimated_complexity": "simple"}
        )
        assert results[0].overall_score >= 0.1

    def test_fallback_score_clamped_maximum(self):
        """Test that score is clamped to maximum 1.0."""
        design = _make_design("Good Design")
        results = self.agent.critique_designs_fallback([design], {})
        assert results[0].overall_score <= 1.0

    def test_fallback_recommendation_quality_tiers(self):
        """Test that recommendation text reflects score tiers."""
        design_good = _make_design(
            "Validated Design",
            agents=[
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
            ],
        )
        results = self.agent.critique_designs_fallback([design_good], {})
        rec = results[0].recommendation.lower()
        assert "solid" in rec or "viable" in rec

    def test_fallback_empty_designs_list(self):
        """Test fallback with empty designs list returns empty results."""
        results = self.agent.critique_designs_fallback([], {})
        assert results == []

    def test_fallback_scalability_notes_for_large_pipeline(self):
        """Test that scalability notes are generated for large pipelines."""
        agents = [
            AgentSpec(
                name=f"agent_{i}",
                role="analyzer",
                llm_model="gpt-4o-mini",
                description=f"Agent {i}",
            )
            for i in range(4)
        ]
        design = _make_design("Large Pipeline", agents=agents)
        results = self.agent.critique_designs_fallback([design], {})
        assert len(results[0].scalability_notes) > 0

    def test_fallback_no_quality_verification_edge_case(self):
        """Test edge case flagged when no critic/cross_checker agent."""
        design = _make_design(
            "No QA",
            agents=[
                AgentSpec(
                    name="analyzer",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="Analyze",
                ),
                AgentSpec(
                    name="reporter",
                    role="reporter",
                    llm_model="gpt-4o-mini",
                    description="Report",
                ),
            ],
        )
        results = self.agent.critique_designs_fallback([design], {})
        edge_text = " ".join(results[0].edge_cases)
        assert (
            "verification" in edge_text.lower() or "hallucination" in edge_text.lower()
        )
