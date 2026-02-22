"""Tests for SessionManager."""

from backend.gateway.session_manager import SessionManager


class TestSessionManager:
    """Tests for conversation-scoped DiscussionEngine management."""

    def test_get_or_create_new_session(self):
        """Test creating a new session."""
        sm = SessionManager(max_sessions=10)
        engine = sm.get_or_create("conv-1")
        assert engine is not None
        assert len(sm) == 1

    def test_get_or_create_existing_session(self):
        """Test retrieving an existing session returns the same engine."""
        sm = SessionManager(max_sessions=10)
        engine1 = sm.get_or_create("conv-1")
        engine2 = sm.get_or_create("conv-1")
        assert engine1 is engine2
        assert len(sm) == 1

    def test_different_conversations_get_different_engines(self):
        """Test different conversation IDs get different engines."""
        sm = SessionManager(max_sessions=10)
        engine1 = sm.get_or_create("conv-1")
        engine2 = sm.get_or_create("conv-2")
        assert engine1 is not engine2
        assert len(sm) == 2

    def test_eviction_at_capacity(self):
        """Test LRU eviction when max sessions is reached."""
        sm = SessionManager(max_sessions=3)
        sm.get_or_create("conv-1")
        sm.get_or_create("conv-2")
        sm.get_or_create("conv-3")
        assert len(sm) == 3

        # Adding a 4th should evict the oldest (conv-1)
        sm.get_or_create("conv-4")
        assert len(sm) == 3

        # conv-1 should be evicted, accessing it creates a new engine
        engine_new = sm.get_or_create("conv-1")
        assert engine_new is not None
        assert len(sm) == 3  # conv-2 evicted now

    def test_access_refreshes_lru(self):
        """Test accessing a session moves it to most-recently-used."""
        sm = SessionManager(max_sessions=3)
        engine1 = sm.get_or_create("conv-1")
        sm.get_or_create("conv-2")
        sm.get_or_create("conv-3")

        # Access conv-1 to refresh it
        sm.get_or_create("conv-1")

        # Now add conv-4, should evict conv-2 (oldest after refresh)
        sm.get_or_create("conv-4")

        # conv-1 should still be the same engine
        assert sm.get_or_create("conv-1") is engine1

    def test_remove(self):
        """Test removing a session."""
        sm = SessionManager(max_sessions=10)
        sm.get_or_create("conv-1")
        assert len(sm) == 1

        sm.remove("conv-1")
        assert len(sm) == 0

    def test_remove_nonexistent(self):
        """Test removing a non-existent session is a no-op."""
        sm = SessionManager(max_sessions=10)
        sm.remove("does-not-exist")  # Should not raise
        assert len(sm) == 0
