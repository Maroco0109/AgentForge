"""Discussion Engine - Main entry point for user interactions."""

import logging

from backend.discussion.intent_analyzer import IntentAnalyzer, IntentResult
from backend.shared.security import sanitize_and_isolate

logger = logging.getLogger(__name__)


class DiscussionEngine:
    """Orchestrates the discussion flow between user and AI agents."""

    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()

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

        # Step 2: Analyze intent
        intent: IntentResult = await self.intent_analyzer.analyze(user_input)

        # Step 3: Build response
        if intent.needs_clarification:
            return {
                "type": "clarification",
                "content": "요청을 더 잘 이해하기 위해 몇 가지 질문이 있습니다.",
                "questions": intent.clarification_questions,
                "partial_intent": {
                    "task": intent.task,
                    "confidence": intent.confidence,
                },
            }

        return {
            "type": "intent_analyzed",
            "content": f"요청을 분석했습니다: {intent.summary}",
            "intent": {
                "task": intent.task,
                "source_type": intent.source_type,
                "source_hints": intent.source_hints,
                "output_format": intent.output_format,
                "confidence": intent.confidence,
                "estimated_complexity": intent.estimated_complexity,
            },
        }
