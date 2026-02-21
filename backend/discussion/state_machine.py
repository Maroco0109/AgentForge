"""Discussion State Machine - Manages discussion flow transitions."""

import enum
import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiscussionState(str, enum.Enum):
    """States in the discussion flow."""

    UNDERSTAND = "understand"  # Analyzing user input
    DESIGN = "design"  # Generating designs
    PRESENT = "present"  # Presenting designs to user
    DEBATE = "debate"  # User feedback + critique
    REFINE = "refine"  # Refining based on feedback
    CONFIRM = "confirm"  # User confirms final design
    PLAN = "plan"  # Generating implementation plan


class StateTransition(BaseModel):
    """Record of a single state transition."""

    from_state: DiscussionState
    to_state: DiscussionState
    event: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)


# Valid transitions: (from_state, event) -> to_state
VALID_TRANSITIONS: dict[tuple[DiscussionState, str], DiscussionState] = {
    # Forward flow
    (DiscussionState.UNDERSTAND, "requirements_analyzed"): DiscussionState.DESIGN,
    (DiscussionState.DESIGN, "designs_generated"): DiscussionState.PRESENT,
    (DiscussionState.PRESENT, "designs_presented"): DiscussionState.DEBATE,
    (DiscussionState.DEBATE, "feedback_received"): DiscussionState.REFINE,
    (DiscussionState.REFINE, "refined_designs_ready"): DiscussionState.PRESENT,
    # User satisfaction shortcuts
    (DiscussionState.PRESENT, "user_satisfied"): DiscussionState.CONFIRM,
    (DiscussionState.DEBATE, "user_satisfied"): DiscussionState.CONFIRM,
    # Confirmation to plan
    (DiscussionState.CONFIRM, "user_confirmed"): DiscussionState.PLAN,
}

# Any state can transition to UNDERSTAND on restart
_RESTART_EVENT = "restart"


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


class DiscussionStateMachine:
    """Manages the discussion state flow with transition validation."""

    def __init__(self, max_rounds: int = 5):
        self.state: DiscussionState = DiscussionState.UNDERSTAND
        self.round: int = 0
        self.max_rounds: int = max_rounds
        self.history: list[StateTransition] = []

    def transition(self, event: str) -> DiscussionState:
        """Transition to next state based on event.

        Args:
            event: The event triggering the transition.

        Returns:
            The new state after transition.

        Raises:
            InvalidTransitionError: If the transition is not valid.
        """
        # Restart is always valid from any state
        if event == _RESTART_EVENT:
            old_state = self.state
            self.state = DiscussionState.UNDERSTAND
            self.round = 0
            self._record_transition(old_state, self.state, event)
            logger.info(f"State restart: {old_state.value} -> {self.state.value}")
            return self.state

        target = VALID_TRANSITIONS.get((self.state, event))
        if target is None:
            raise InvalidTransitionError(
                f"No valid transition from '{self.state.value}' with event '{event}'. "
                f"Valid events from '{self.state.value}': "
                f"{[e for (s, e) in VALID_TRANSITIONS if s == self.state]}"
            )

        old_state = self.state
        self.state = target

        # Increment round counter on PRESENT -> DEBATE cycle
        if old_state == DiscussionState.PRESENT and target == DiscussionState.DEBATE:
            self.round += 1

        self._record_transition(old_state, target, event)
        logger.info(
            f"State transition: {old_state.value} -> {target.value} "
            f"(event={event}, round={self.round})"
        )
        return self.state

    def can_transition(self, target: DiscussionState) -> bool:
        """Check if a transition to the target state is possible."""
        if target == DiscussionState.UNDERSTAND:
            return True  # Restart is always valid
        return any(
            to == target
            for (from_state, _), to in VALID_TRANSITIONS.items()
            if from_state == self.state
        )

    def force_decision_mode(self) -> bool:
        """Check if we should force a decision (max rounds reached)."""
        return self.round >= self.max_rounds

    def get_valid_events(self) -> list[str]:
        """Get list of valid events from the current state."""
        events = [e for (s, e) in VALID_TRANSITIONS if s == self.state]
        events.append(_RESTART_EVENT)
        return events

    def _record_transition(
        self,
        from_state: DiscussionState,
        to_state: DiscussionState,
        event: str,
    ) -> None:
        """Record a transition in history."""
        self.history.append(
            StateTransition(
                from_state=from_state,
                to_state=to_state,
                event=event,
            )
        )

    def to_dict(self) -> dict:
        """Serialize state machine to dict."""
        return {
            "state": self.state.value,
            "round": self.round,
            "max_rounds": self.max_rounds,
            "history": [t.model_dump(mode="json") for t in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiscussionStateMachine":
        """Deserialize state machine from dict."""
        sm = cls(max_rounds=data.get("max_rounds", 5))
        sm.state = DiscussionState(data["state"])
        sm.round = data.get("round", 0)
        sm.history = [StateTransition(**t) for t in data.get("history", [])]
        return sm
