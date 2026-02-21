"""Discussion Engine - Main entry point for user interactions."""

import logging

from backend.discussion.critique_agent import CritiqueAgent, CritiqueResult
from backend.discussion.design_generator import DesignGenerator, DesignProposal
from backend.discussion.intent_analyzer import IntentAnalyzer, IntentResult
from backend.discussion.memory import DiscussionMemory
from backend.discussion.state_machine import (
    DiscussionState,
    DiscussionStateMachine,
    InvalidTransitionError,
)
from backend.shared.security import sanitize_and_isolate

logger = logging.getLogger(__name__)


class DiscussionEngine:
    """Orchestrates the discussion flow between user and AI agents.

    Integrates intent analysis, design generation, critique,
    state management, and discussion memory.
    """

    def __init__(self, max_rounds: int = 5):
        self.intent_analyzer = IntentAnalyzer()
        self.design_generator = DesignGenerator()
        self.critique_agent = CritiqueAgent()
        self.state_machine = DiscussionStateMachine(max_rounds=max_rounds)
        self.memory = DiscussionMemory()

        # Current session state
        self._current_intent: IntentResult | None = None
        self._current_designs: list[DesignProposal] = []
        self._current_critiques: list[CritiqueResult] = []

    async def process_message(self, user_input: str) -> dict:
        """Process a user message through the discussion engine.

        Returns a structured response dict.
        """
        # Step 1: Security check
        isolated_input, is_safe, injection_matches = sanitize_and_isolate(user_input)

        if not is_safe:
            logger.warning(f"Injection attempt detected: {injection_matches}")
            return {
                "type": "security_warning",
                "content": "입력에서 잠재적 보안 위험이 감지되었습니다. 요청을 다시 작성해주세요.",
                "safe": False,
            }

        # Step 2: Route based on current state
        state = self.state_machine.state
        try:
            if state == DiscussionState.UNDERSTAND:
                return await self._handle_understand(isolated_input)
            elif state == DiscussionState.DESIGN:
                return await self._handle_design()
            elif state == DiscussionState.PRESENT:
                return await self._handle_present()
            elif state == DiscussionState.DEBATE:
                return await self._handle_debate(isolated_input)
            elif state == DiscussionState.REFINE:
                return await self._handle_refine(isolated_input)
            elif state == DiscussionState.CONFIRM:
                return await self._handle_confirm(isolated_input)
            elif state == DiscussionState.PLAN:
                return await self._handle_plan()
            else:
                return {
                    "type": "error",
                    "content": f"Unknown state: {state.value}",
                    "state": state.value,
                }
        except InvalidTransitionError as e:
            logger.error(f"Invalid state transition: {e}")
            return {
                "type": "error",
                "content": str(e),
                "state": self.state_machine.state.value,
                "valid_events": self.state_machine.get_valid_events(),
            }

    async def start_discussion(self, user_input: str) -> dict:
        """Start a new discussion from scratch.

        Resets state and processes the initial user input.
        """
        self.state_machine = DiscussionStateMachine(max_rounds=self.state_machine.max_rounds)
        self.memory = DiscussionMemory()
        self._current_intent = None
        self._current_designs = []
        self._current_critiques = []
        return await self.process_message(user_input)

    async def process_user_input(self, user_input: str) -> dict:
        """Process user input in the context of the current discussion.

        Alias for process_message that makes the API more intuitive.
        """
        return await self.process_message(user_input)

    def get_current_state(self) -> dict:
        """Get the current state of the discussion."""
        return {
            "state": self.state_machine.state.value,
            "round": self.state_machine.round,
            "max_rounds": self.state_machine.max_rounds,
            "force_decision": self.state_machine.force_decision_mode(),
            "valid_events": self.state_machine.get_valid_events(),
            "has_designs": len(self._current_designs) > 0,
            "has_critiques": len(self._current_critiques) > 0,
            "memory_summary": {
                "agreements": len(self.memory.agreements),
                "open_questions": len(self.memory.open_questions),
                "preferences": len(self.memory.user_preferences),
                "rounds_completed": len(self.memory.round_summaries),
            },
        }

    # --- State handlers ---

    async def _handle_understand(self, isolated_input: str) -> dict:
        """Handle UNDERSTAND state: analyze user intent."""
        intent: IntentResult = await self.intent_analyzer.analyze(isolated_input)
        self._current_intent = intent

        if intent.needs_clarification:
            return {
                "type": "clarification",
                "content": "요청을 더 잘 이해하기 위해 몇 가지 질문이 있습니다.",
                "questions": intent.clarification_questions,
                "partial_intent": {
                    "task": intent.task,
                    "confidence": intent.confidence,
                },
                "state": DiscussionState.UNDERSTAND.value,
            }

        # Transition to DESIGN
        self.state_machine.transition("requirements_analyzed")

        # Immediately proceed to design generation
        return await self._handle_design()

    async def _handle_design(self) -> dict:
        """Handle DESIGN state: generate design proposals."""
        if self._current_intent is None:
            return {
                "type": "error",
                "content": "No intent available. Please provide your requirements first.",
                "state": DiscussionState.DESIGN.value,
            }

        requirements = {
            "task": self._current_intent.task,
            "source_type": self._current_intent.source_type,
            "source_hints": self._current_intent.source_hints,
            "output_format": self._current_intent.output_format,
            "estimated_complexity": self._current_intent.estimated_complexity,
        }

        context = self.memory.get_context_for_llm()
        self._current_designs = await self.design_generator.generate_designs(requirements, context)

        # Record in memory
        self.memory.add_design_snapshot([d.model_dump() for d in self._current_designs])

        # Transition to PRESENT
        self.state_machine.transition("designs_generated")

        return await self._handle_present()

    async def _handle_present(self) -> dict:
        """Handle PRESENT state: present designs to user."""
        designs_data = []
        for design in self._current_designs:
            designs_data.append(design.model_dump())

        # Check if we should force a decision
        force_decision = self.state_machine.force_decision_mode()

        # Transition to DEBATE
        self.state_machine.transition("designs_presented")

        response = {
            "type": "designs_presented",
            "content": "다음과 같은 파이프라인 설계안을 생성했습니다.",
            "designs": designs_data,
            "state": DiscussionState.DEBATE.value,
            "round": self.state_machine.round,
        }

        if force_decision:
            response["force_decision"] = True
            response["content"] += " 최대 논의 횟수에 도달했습니다. 설계안을 선택해주세요."

        if self._current_critiques:
            response["critiques"] = [c.model_dump() for c in self._current_critiques]

        return response

    async def _handle_debate(self, user_input: str) -> dict:
        """Handle DEBATE state: process user feedback."""
        input_lower = user_input.lower()

        # Check for satisfaction signals
        satisfaction_signals = [
            "좋아",
            "괜찮",
            "확인",
            "선택",
            "결정",
            "ok",
            "good",
            "confirm",
            "select",
            "choose",
            "이걸로",
            "이것으로",
            "승인",
            "동의",
        ]

        if any(signal in input_lower for signal in satisfaction_signals):
            # User is satisfied
            self.memory.add_agreement(f"User approved design: {user_input}")
            self.state_machine.transition("user_satisfied")
            return await self._handle_confirm(user_input)

        # User has feedback - run critique and refine
        self.memory.add_open_question(f"User feedback: {user_input}")

        # Run critique on current designs
        if self._current_intent:
            requirements = {
                "task": self._current_intent.task,
                "source_type": self._current_intent.source_type,
                "estimated_complexity": self._current_intent.estimated_complexity,
            }
        else:
            requirements = {}

        self._current_critiques = await self.critique_agent.critique_designs(
            self._current_designs, requirements
        )

        # Record in memory
        self.memory.add_critique_snapshot([c.model_dump() for c in self._current_critiques])

        self.memory.add_round_summary(
            f"Round {self.state_machine.round}: "
            f"User feedback: {user_input[:100]}. "
            f"Critique scores: {[c.overall_score for c in self._current_critiques]}"
        )

        # Transition to REFINE
        self.state_machine.transition("feedback_received")

        return {
            "type": "critique_complete",
            "content": "설계안에 대한 분석이 완료되었습니다. 피드백을 반영하여 수정하겠습니다.",
            "critiques": [c.model_dump() for c in self._current_critiques],
            "state": DiscussionState.REFINE.value,
            "round": self.state_machine.round,
        }

    async def _handle_refine(self, user_input: str) -> dict:
        """Handle REFINE state: refine designs based on feedback."""
        # Store user preferences from feedback
        self.memory.set_preference(f"feedback_round_{self.state_machine.round}", user_input)

        # Re-generate designs with updated context
        if self._current_intent:
            requirements = {
                "task": self._current_intent.task,
                "source_type": self._current_intent.source_type,
                "source_hints": self._current_intent.source_hints,
                "output_format": self._current_intent.output_format,
                "estimated_complexity": self._current_intent.estimated_complexity,
            }
        else:
            requirements = {}

        context = self.memory.get_context_for_llm()
        self._current_designs = await self.design_generator.generate_designs(requirements, context)

        self.memory.add_design_snapshot([d.model_dump() for d in self._current_designs])

        # Transition back to PRESENT
        self.state_machine.transition("refined_designs_ready")

        return await self._handle_present()

    async def _handle_confirm(self, user_input: str) -> dict:
        """Handle CONFIRM state: user confirms final design."""
        # Find the selected/recommended design
        selected_design = None
        input_lower = user_input.lower()

        # Try to match by design name or number
        for i, design in enumerate(self._current_designs):
            if design.name.lower() in input_lower or str(i + 1) in user_input:
                selected_design = design
                break

        # Default to recommended design
        if selected_design is None:
            for design in self._current_designs:
                if design.recommended:
                    selected_design = design
                    break

        # Fallback to first design
        if selected_design is None and self._current_designs:
            selected_design = self._current_designs[0]

        if selected_design is None:
            return {
                "type": "error",
                "content": "선택할 수 있는 설계안이 없습니다. 처음부터 다시 시작해주세요.",
                "state": DiscussionState.CONFIRM.value,
            }

        self.memory.add_agreement(f"Final design selected: {selected_design.name}")

        # Transition to PLAN
        self.state_machine.transition("user_confirmed")

        return {
            "type": "design_confirmed",
            "content": f"'{selected_design.name}' 설계안이 확정되었습니다. 실행 계획을 생성합니다.",
            "selected_design": selected_design.model_dump(),
            "state": DiscussionState.PLAN.value,
            "memory": self.memory.to_dict(),
        }

    async def _handle_plan(self) -> dict:
        """Handle PLAN state: generate implementation plan."""
        # Find the confirmed design
        selected_design = None
        for design in self._current_designs:
            if any(design.name in agreement for agreement in self.memory.agreements):
                selected_design = design
                break

        if selected_design is None and self._current_designs:
            selected_design = self._current_designs[0]

        return {
            "type": "plan_generated",
            "content": "파이프라인 실행 계획이 준비되었습니다.",
            "selected_design": selected_design.model_dump() if selected_design else None,
            "state": DiscussionState.PLAN.value,
            "discussion_summary": {
                "total_rounds": self.state_machine.round,
                "agreements": self.memory.agreements,
                "preferences": self.memory.user_preferences,
            },
        }

    def to_dict(self) -> dict:
        """Serialize the entire engine state for persistence."""
        return {
            "state_machine": self.state_machine.to_dict(),
            "memory": self.memory.to_dict(),
            "current_intent": {
                "task": self._current_intent.task,
                "source_type": self._current_intent.source_type,
                "source_hints": self._current_intent.source_hints,
                "output_format": self._current_intent.output_format,
                "estimated_complexity": self._current_intent.estimated_complexity,
                "confidence": self._current_intent.confidence,
                "summary": self._current_intent.summary,
            }
            if self._current_intent
            else None,
            "current_designs": [d.model_dump() for d in self._current_designs],
            "current_critiques": [c.model_dump() for c in self._current_critiques],
        }
