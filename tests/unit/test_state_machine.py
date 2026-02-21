"""Tests for Discussion State Machine - State transitions and flow control."""

import pytest

from backend.discussion.state_machine import (
    DiscussionState,
    DiscussionStateMachine,
    InvalidTransitionError,
    StateTransition,
)


class TestDiscussionState:
    """Test DiscussionState enum."""

    def test_has_all_seven_states(self):
        """Test that DiscussionState enum has exactly 7 states."""
        states = list(DiscussionState)
        assert len(states) == 7

    def test_state_values(self):
        """Test each state has the correct string value."""
        assert DiscussionState.UNDERSTAND == "understand"
        assert DiscussionState.DESIGN == "design"
        assert DiscussionState.PRESENT == "present"
        assert DiscussionState.DEBATE == "debate"
        assert DiscussionState.REFINE == "refine"
        assert DiscussionState.CONFIRM == "confirm"
        assert DiscussionState.PLAN == "plan"

    def test_states_are_strings(self):
        """Test that states are string enums."""
        for state in DiscussionState:
            assert isinstance(state, str)
            assert isinstance(state.value, str)


class TestStateTransition:
    """Test StateTransition model."""

    def test_create_transition(self):
        """Test creating a StateTransition record."""
        t = StateTransition(
            from_state=DiscussionState.UNDERSTAND,
            to_state=DiscussionState.DESIGN,
            event="requirements_analyzed",
        )
        assert t.from_state == DiscussionState.UNDERSTAND
        assert t.to_state == DiscussionState.DESIGN
        assert t.event == "requirements_analyzed"
        assert t.timestamp is not None
        assert t.metadata == {}

    def test_transition_with_metadata(self):
        """Test creating a StateTransition with metadata."""
        t = StateTransition(
            from_state=DiscussionState.PRESENT,
            to_state=DiscussionState.DEBATE,
            event="designs_presented",
            metadata={"round": 1},
        )
        assert t.metadata == {"round": 1}


class TestDiscussionStateMachine:
    """Test DiscussionStateMachine logic."""

    def setup_method(self):
        """Setup test fixtures."""
        self.sm = DiscussionStateMachine()

    def test_initial_state_is_understand(self):
        """Test that initial state is UNDERSTAND."""
        assert self.sm.state == DiscussionState.UNDERSTAND

    def test_initial_round_is_zero(self):
        """Test that initial round counter is 0."""
        assert self.sm.round == 0

    def test_default_max_rounds_is_five(self):
        """Test that default max_rounds is 5."""
        assert self.sm.max_rounds == 5

    def test_custom_max_rounds(self):
        """Test creating state machine with custom max_rounds."""
        sm = DiscussionStateMachine(max_rounds=3)
        assert sm.max_rounds == 3

    def test_initial_history_is_empty(self):
        """Test that initial history is empty."""
        assert self.sm.history == []

    def test_understand_to_design(self):
        """Test UNDERSTAND -> DESIGN transition."""
        new_state = self.sm.transition("requirements_analyzed")
        assert new_state == DiscussionState.DESIGN
        assert self.sm.state == DiscussionState.DESIGN

    def test_design_to_present(self):
        """Test DESIGN -> PRESENT transition."""
        self.sm.state = DiscussionState.DESIGN
        new_state = self.sm.transition("designs_generated")
        assert new_state == DiscussionState.PRESENT

    def test_present_to_debate(self):
        """Test PRESENT -> DEBATE transition."""
        self.sm.state = DiscussionState.PRESENT
        new_state = self.sm.transition("designs_presented")
        assert new_state == DiscussionState.DEBATE

    def test_present_to_confirm(self):
        """Test PRESENT -> CONFIRM transition (user satisfied shortcut)."""
        self.sm.state = DiscussionState.PRESENT
        new_state = self.sm.transition("user_satisfied")
        assert new_state == DiscussionState.CONFIRM

    def test_debate_to_refine(self):
        """Test DEBATE -> REFINE transition."""
        self.sm.state = DiscussionState.DEBATE
        new_state = self.sm.transition("feedback_received")
        assert new_state == DiscussionState.REFINE

    def test_debate_to_confirm(self):
        """Test DEBATE -> CONFIRM transition (user satisfied)."""
        self.sm.state = DiscussionState.DEBATE
        new_state = self.sm.transition("user_satisfied")
        assert new_state == DiscussionState.CONFIRM

    def test_refine_to_present(self):
        """Test REFINE -> PRESENT transition."""
        self.sm.state = DiscussionState.REFINE
        new_state = self.sm.transition("refined_designs_ready")
        assert new_state == DiscussionState.PRESENT

    def test_confirm_to_plan(self):
        """Test CONFIRM -> PLAN transition."""
        self.sm.state = DiscussionState.CONFIRM
        new_state = self.sm.transition("user_confirmed")
        assert new_state == DiscussionState.PLAN

    def test_restart_from_any_state(self):
        """Test that restart transitions to UNDERSTAND from any state."""
        for state in DiscussionState:
            sm = DiscussionStateMachine()
            sm.state = state
            new_state = sm.transition("restart")
            assert new_state == DiscussionState.UNDERSTAND
            assert sm.round == 0

    def test_invalid_transition_raises_error(self):
        """Test that invalid transitions raise InvalidTransitionError."""
        with pytest.raises(InvalidTransitionError):
            self.sm.transition("user_satisfied")

    def test_invalid_transition_from_plan(self):
        """Test that PLAN state has no forward transitions."""
        self.sm.state = DiscussionState.PLAN
        with pytest.raises(InvalidTransitionError):
            self.sm.transition("designs_generated")

    def test_invalid_transition_from_confirm(self):
        """Test invalid event from CONFIRM state."""
        self.sm.state = DiscussionState.CONFIRM
        with pytest.raises(InvalidTransitionError):
            self.sm.transition("feedback_received")

    def test_invalid_event_name(self):
        """Test that a completely unknown event raises error."""
        with pytest.raises(InvalidTransitionError):
            self.sm.transition("nonexistent_event")

    def test_invalid_transition_error_message_contains_state(self):
        """Test that error message contains the current state."""
        with pytest.raises(InvalidTransitionError, match="understand"):
            self.sm.transition("user_confirmed")

    def test_round_increments_on_present_to_debate(self):
        """Test round counter increments on PRESENT -> DEBATE cycle."""
        self.sm.state = DiscussionState.PRESENT
        self.sm.transition("designs_presented")
        assert self.sm.round == 1

    def test_round_increments_only_on_present_to_debate(self):
        """Test round counter does NOT increment on other transitions."""
        self.sm.transition("requirements_analyzed")
        assert self.sm.round == 0
        self.sm.transition("designs_generated")
        assert self.sm.round == 0

    def test_multiple_rounds(self):
        """Test round counter over multiple PRESENT -> DEBATE cycles."""
        self.sm.state = DiscussionState.PRESENT
        self.sm.transition("designs_presented")
        assert self.sm.round == 1
        self.sm.transition("feedback_received")
        self.sm.transition("refined_designs_ready")
        self.sm.transition("designs_presented")
        assert self.sm.round == 2

    def test_restart_resets_round(self):
        """Test that restart resets the round counter to 0."""
        self.sm.state = DiscussionState.PRESENT
        self.sm.transition("designs_presented")
        assert self.sm.round == 1
        self.sm.transition("restart")
        assert self.sm.round == 0

    def test_force_decision_mode_false_when_below_max(self):
        """Test force_decision_mode returns False when rounds < max."""
        assert self.sm.force_decision_mode() is False

    def test_force_decision_mode_true_when_max_reached(self):
        """Test force_decision_mode returns True when max_rounds reached."""
        self.sm.round = 5
        assert self.sm.force_decision_mode() is True

    def test_force_decision_mode_true_when_exceeds_max(self):
        """Test force_decision_mode returns True when rounds exceed max."""
        self.sm.round = 10
        assert self.sm.force_decision_mode() is True

    def test_force_decision_mode_custom_max(self):
        """Test force_decision_mode with custom max_rounds."""
        sm = DiscussionStateMachine(max_rounds=2)
        sm.round = 2
        assert sm.force_decision_mode() is True
        sm.round = 1
        assert sm.force_decision_mode() is False

    def test_get_valid_events_understand(self):
        """Test valid events from UNDERSTAND state."""
        events = self.sm.get_valid_events()
        assert "requirements_analyzed" in events
        assert "restart" in events

    def test_get_valid_events_present(self):
        """Test valid events from PRESENT state."""
        self.sm.state = DiscussionState.PRESENT
        events = self.sm.get_valid_events()
        assert "designs_presented" in events
        assert "user_satisfied" in events
        assert "restart" in events

    def test_get_valid_events_debate(self):
        """Test valid events from DEBATE state."""
        self.sm.state = DiscussionState.DEBATE
        events = self.sm.get_valid_events()
        assert "feedback_received" in events
        assert "user_satisfied" in events
        assert "restart" in events

    def test_get_valid_events_always_includes_restart(self):
        """Test that restart is always a valid event."""
        for state in DiscussionState:
            self.sm.state = state
            events = self.sm.get_valid_events()
            assert "restart" in events

    def test_can_transition_to_understand_always(self):
        """Test can_transition to UNDERSTAND is always True."""
        for state in DiscussionState:
            self.sm.state = state
            assert self.sm.can_transition(DiscussionState.UNDERSTAND) is True

    def test_can_transition_valid(self):
        """Test can_transition for valid target."""
        assert self.sm.can_transition(DiscussionState.DESIGN) is True

    def test_can_transition_invalid(self):
        """Test can_transition for invalid target."""
        assert self.sm.can_transition(DiscussionState.PLAN) is False

    def test_get_history_empty(self):
        """Test history is empty initially."""
        assert len(self.sm.history) == 0

    def test_get_history_records_transitions(self):
        """Test history records each transition."""
        self.sm.transition("requirements_analyzed")
        assert len(self.sm.history) == 1
        assert self.sm.history[0].from_state == DiscussionState.UNDERSTAND
        assert self.sm.history[0].to_state == DiscussionState.DESIGN
        assert self.sm.history[0].event == "requirements_analyzed"

    def test_get_history_multiple_transitions(self):
        """Test history accumulates transitions."""
        self.sm.transition("requirements_analyzed")
        self.sm.transition("designs_generated")
        assert len(self.sm.history) == 2
        assert self.sm.history[1].from_state == DiscussionState.DESIGN
        assert self.sm.history[1].to_state == DiscussionState.PRESENT

    def test_restart_records_in_history(self):
        """Test that restart is recorded in history."""
        self.sm.state = DiscussionState.DEBATE
        self.sm.transition("restart")
        assert len(self.sm.history) == 1
        assert self.sm.history[0].from_state == DiscussionState.DEBATE
        assert self.sm.history[0].to_state == DiscussionState.UNDERSTAND
        assert self.sm.history[0].event == "restart"

    def test_to_dict(self):
        """Test serialization to dict."""
        self.sm.transition("requirements_analyzed")
        data = self.sm.to_dict()
        assert data["state"] == "design"
        assert data["round"] == 0
        assert data["max_rounds"] == 5
        assert len(data["history"]) == 1

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "state": "debate",
            "round": 3,
            "max_rounds": 10,
            "history": [],
        }
        sm = DiscussionStateMachine.from_dict(data)
        assert sm.state == DiscussionState.DEBATE
        assert sm.round == 3
        assert sm.max_rounds == 10
        assert sm.history == []

    def test_to_dict_from_dict_round_trip(self):
        """Test serialization round-trip preserves state."""
        self.sm.transition("requirements_analyzed")
        self.sm.transition("designs_generated")
        data = self.sm.to_dict()
        sm2 = DiscussionStateMachine.from_dict(data)
        assert sm2.state == self.sm.state
        assert sm2.round == self.sm.round
        assert sm2.max_rounds == self.sm.max_rounds
        assert len(sm2.history) == len(self.sm.history)

    def test_from_dict_defaults(self):
        """Test from_dict with minimal data uses defaults."""
        data = {"state": "understand"}
        sm = DiscussionStateMachine.from_dict(data)
        assert sm.round == 0
        assert sm.max_rounds == 5
        assert sm.history == []

    def test_full_happy_path_flow(self):
        """Test complete flow: UNDERSTAND -> DESIGN -> PRESENT -> DEBATE -> CONFIRM -> PLAN."""
        assert self.sm.state == DiscussionState.UNDERSTAND
        self.sm.transition("requirements_analyzed")
        assert self.sm.state == DiscussionState.DESIGN
        self.sm.transition("designs_generated")
        assert self.sm.state == DiscussionState.PRESENT
        self.sm.transition("designs_presented")
        assert self.sm.state == DiscussionState.DEBATE
        assert self.sm.round == 1
        self.sm.transition("user_satisfied")
        assert self.sm.state == DiscussionState.CONFIRM
        self.sm.transition("user_confirmed")
        assert self.sm.state == DiscussionState.PLAN
        assert len(self.sm.history) == 5

    def test_full_refinement_flow(self):
        """Test flow with refinement cycle."""
        self.sm.transition("requirements_analyzed")
        self.sm.transition("designs_generated")
        self.sm.transition("designs_presented")
        self.sm.transition("feedback_received")
        self.sm.transition("refined_designs_ready")
        self.sm.transition("designs_presented")
        self.sm.transition("user_satisfied")
        self.sm.transition("user_confirmed")
        assert self.sm.state == DiscussionState.PLAN
        assert self.sm.round == 2
