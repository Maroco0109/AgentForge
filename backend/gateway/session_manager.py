"""Session manager for conversation-scoped DiscussionEngine instances."""

from collections import OrderedDict

from backend.discussion.engine import DiscussionEngine

DEFAULT_MAX_SESSIONS = 500


class SessionManager:
    """Manages DiscussionEngine instances per conversation.

    Uses OrderedDict for LRU eviction when max sessions is reached.
    """

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS):
        self.max_sessions = max_sessions
        self._sessions: OrderedDict[str, DiscussionEngine] = OrderedDict()

    def get_or_create(self, conversation_id: str) -> DiscussionEngine:
        """Get existing engine or create a new one for this conversation."""
        if conversation_id in self._sessions:
            # Move to end (most recently used)
            self._sessions.move_to_end(conversation_id)
            return self._sessions[conversation_id]

        # Evict oldest if at capacity
        while len(self._sessions) >= self.max_sessions:
            self._sessions.popitem(last=False)

        engine = DiscussionEngine()
        self._sessions[conversation_id] = engine
        return engine

    def remove(self, conversation_id: str) -> None:
        """Remove a session."""
        self._sessions.pop(conversation_id, None)

    def __len__(self) -> int:
        return len(self._sessions)


# Module-level singleton
session_manager = SessionManager()
