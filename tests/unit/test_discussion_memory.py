"""Tests for Discussion Memory - Tracks agreements, preferences, and history."""

from backend.discussion.memory import DiscussionMemory


class TestDiscussionMemory:
    """Test DiscussionMemory functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.memory = DiscussionMemory()

    # --- Initialization ---

    def test_empty_initialization(self):
        """Test that memory initializes with empty collections."""
        assert self.memory.agreements == []
        assert self.memory.open_questions == []
        assert self.memory.user_preferences == {}
        assert self.memory.design_history == []
        assert self.memory.critique_history == []
        assert self.memory.round_summaries == []
        assert self.memory.resolved_questions == []

    # --- Agreements ---

    def test_add_agreement(self):
        """Test adding an agreement."""
        self.memory.add_agreement("Use gpt-4o-mini for cost efficiency")
        assert len(self.memory.agreements) == 1
        assert self.memory.agreements[0] == "Use gpt-4o-mini for cost efficiency"

    def test_add_multiple_agreements(self):
        """Test adding multiple agreements."""
        self.memory.add_agreement("Agreement 1")
        self.memory.add_agreement("Agreement 2")
        assert len(self.memory.agreements) == 2

    def test_add_duplicate_agreement_ignored(self):
        """Test that duplicate agreements are not added."""
        self.memory.add_agreement("Same agreement")
        self.memory.add_agreement("Same agreement")
        assert len(self.memory.agreements) == 1

    # --- Open questions ---

    def test_add_open_question(self):
        """Test adding an open question."""
        self.memory.add_open_question("What data format?")
        assert len(self.memory.open_questions) == 1
        assert self.memory.open_questions[0] == "What data format?"

    def test_add_duplicate_question_ignored(self):
        """Test that duplicate questions are not added."""
        self.memory.add_open_question("Same question?")
        self.memory.add_open_question("Same question?")
        assert len(self.memory.open_questions) == 1

    def test_resolve_question(self):
        """Test resolving an open question."""
        self.memory.add_open_question("What format?")
        self.memory.resolve_question("What format?", "JSON")
        assert len(self.memory.open_questions) == 0
        assert len(self.memory.resolved_questions) == 1
        assert self.memory.resolved_questions[0]["question"] == "What format?"
        assert self.memory.resolved_questions[0]["resolution"] == "JSON"

    def test_resolve_nonexistent_question(self):
        """Test resolving a question that does not exist does nothing."""
        self.memory.resolve_question("Not a question", "Some answer")
        assert len(self.memory.resolved_questions) == 0
        assert len(self.memory.open_questions) == 0

    def test_resolve_question_removes_from_open(self):
        """Test that resolving removes from open_questions list."""
        self.memory.add_open_question("Q1")
        self.memory.add_open_question("Q2")
        self.memory.resolve_question("Q1", "Answer 1")
        assert "Q1" not in self.memory.open_questions
        assert "Q2" in self.memory.open_questions

    # --- Preferences ---

    def test_set_preference(self):
        """Test setting a user preference."""
        self.memory.set_preference("cost_priority", "low")
        assert self.memory.user_preferences["cost_priority"] == "low"

    def test_set_preference_overwrite(self):
        """Test overwriting an existing preference."""
        self.memory.set_preference("cost_priority", "low")
        self.memory.set_preference("cost_priority", "high")
        assert self.memory.user_preferences["cost_priority"] == "high"

    def test_set_preference_various_types(self):
        """Test preferences with various value types."""
        self.memory.set_preference("count", 5)
        self.memory.set_preference("enabled", True)
        self.memory.set_preference("tags", ["a", "b"])
        assert self.memory.user_preferences["count"] == 5
        assert self.memory.user_preferences["enabled"] is True
        assert self.memory.user_preferences["tags"] == ["a", "b"]

    # --- Design history ---

    def test_add_design_snapshot(self):
        """Test adding a design snapshot."""
        designs = [{"name": "Design A"}, {"name": "Design B"}]
        self.memory.add_design_snapshot(designs)
        assert len(self.memory.design_history) == 1
        assert self.memory.design_history[0]["round"] == 0
        assert self.memory.design_history[0]["designs"] == designs

    def test_design_history_auto_increments_round(self):
        """Test that design_history round auto-increments."""
        self.memory.add_design_snapshot([{"name": "v1"}])
        self.memory.add_design_snapshot([{"name": "v2"}])
        assert self.memory.design_history[0]["round"] == 0
        assert self.memory.design_history[1]["round"] == 1

    # --- Critique history ---

    def test_add_critique_snapshot(self):
        """Test adding a critique snapshot."""
        critiques = [{"design_name": "Design A", "score": 0.8}]
        self.memory.add_critique_snapshot(critiques)
        assert len(self.memory.critique_history) == 1
        assert self.memory.critique_history[0]["round"] == 0
        assert self.memory.critique_history[0]["critiques"] == critiques

    def test_critique_history_auto_increments_round(self):
        """Test that critique_history round auto-increments."""
        self.memory.add_critique_snapshot([{"score": 0.7}])
        self.memory.add_critique_snapshot([{"score": 0.8}])
        assert self.memory.critique_history[0]["round"] == 0
        assert self.memory.critique_history[1]["round"] == 1

    # --- Round summaries ---

    def test_add_round_summary(self):
        """Test adding a round summary."""
        self.memory.add_round_summary("Round 1: User requested data collection")
        assert len(self.memory.round_summaries) == 1
        assert (
            self.memory.round_summaries[0] == "Round 1: User requested data collection"
        )

    def test_multiple_round_summaries(self):
        """Test adding multiple round summaries."""
        self.memory.add_round_summary("Round 1 summary")
        self.memory.add_round_summary("Round 2 summary")
        assert len(self.memory.round_summaries) == 2

    # --- get_context_for_llm ---

    def test_get_context_empty_memory(self):
        """Test context string for empty memory."""
        context = self.memory.get_context_for_llm()
        assert context == "No prior discussion context."

    def test_get_context_with_agreements(self):
        """Test context string includes agreements."""
        self.memory.add_agreement("Use simple pipeline")
        context = self.memory.get_context_for_llm()
        assert "Agreed Decisions" in context
        assert "Use simple pipeline" in context

    def test_get_context_with_open_questions(self):
        """Test context string includes open questions."""
        self.memory.add_open_question("What about error handling?")
        context = self.memory.get_context_for_llm()
        assert "Open Questions" in context
        assert "What about error handling?" in context

    def test_get_context_with_preferences(self):
        """Test context string includes user preferences."""
        self.memory.set_preference("cost", "low")
        context = self.memory.get_context_for_llm()
        assert "User Preferences" in context
        assert "cost: low" in context

    def test_get_context_with_round_summaries(self):
        """Test context string includes round summaries."""
        self.memory.add_round_summary("Discussed pipeline options")
        context = self.memory.get_context_for_llm()
        assert "Previous Round Summaries" in context
        assert "Discussed pipeline options" in context

    def test_get_context_with_resolved_questions(self):
        """Test context string includes resolved questions."""
        self.memory.add_open_question("Format?")
        self.memory.resolve_question("Format?", "JSON")
        context = self.memory.get_context_for_llm()
        assert "Resolved Questions" in context
        assert "Format?" in context
        assert "JSON" in context

    def test_get_context_returns_string(self):
        """Test that get_context_for_llm always returns a string."""
        self.memory.add_agreement("Something")
        self.memory.add_open_question("Question?")
        context = self.memory.get_context_for_llm()
        assert isinstance(context, str)
        assert len(context) > 0

    def test_get_context_comprehensive(self):
        """Test context with all sections populated."""
        self.memory.add_agreement("Agreed on design A")
        self.memory.add_open_question("Scalability?")
        self.memory.set_preference("speed", "fast")
        self.memory.add_round_summary("Round 1 done")
        self.memory.add_open_question("Cost?")
        self.memory.resolve_question("Cost?", "Under 0.10")
        context = self.memory.get_context_for_llm()
        assert "Agreed Decisions" in context
        assert "Open Questions" in context
        assert "User Preferences" in context
        assert "Previous Round Summaries" in context
        assert "Resolved Questions" in context

    # --- Serialization ---

    def test_to_dict(self):
        """Test serialization to dict."""
        self.memory.add_agreement("A1")
        self.memory.set_preference("key", "val")
        data = self.memory.to_dict()
        assert data["agreements"] == ["A1"]
        assert data["user_preferences"] == {"key": "val"}
        assert "open_questions" in data
        assert "design_history" in data
        assert "critique_history" in data
        assert "round_summaries" in data
        assert "resolved_questions" in data

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "agreements": ["A1", "A2"],
            "open_questions": ["Q1"],
            "user_preferences": {"k": "v"},
            "design_history": [],
            "critique_history": [],
            "round_summaries": ["Summary 1"],
            "resolved_questions": [{"question": "Q0", "resolution": "R0"}],
        }
        memory = DiscussionMemory.from_dict(data)
        assert memory.agreements == ["A1", "A2"]
        assert memory.open_questions == ["Q1"]
        assert memory.user_preferences == {"k": "v"}
        assert memory.round_summaries == ["Summary 1"]
        assert memory.resolved_questions == [{"question": "Q0", "resolution": "R0"}]

    def test_to_dict_from_dict_round_trip(self):
        """Test serialization round-trip preserves all data."""
        self.memory.add_agreement("Agreed")
        self.memory.add_open_question("Open?")
        self.memory.set_preference("pref", "value")
        self.memory.add_design_snapshot([{"name": "D1"}])
        self.memory.add_critique_snapshot([{"score": 0.8}])
        self.memory.add_round_summary("Summary")
        self.memory.resolve_question("Open?", "Resolved")
        data = self.memory.to_dict()
        restored = DiscussionMemory.from_dict(data)
        assert restored.agreements == self.memory.agreements
        assert restored.open_questions == self.memory.open_questions
        assert restored.user_preferences == self.memory.user_preferences
        assert restored.design_history == self.memory.design_history
        assert restored.critique_history == self.memory.critique_history
        assert restored.round_summaries == self.memory.round_summaries
        assert restored.resolved_questions == self.memory.resolved_questions
