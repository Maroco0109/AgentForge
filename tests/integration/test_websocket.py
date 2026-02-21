"""Tests for WebSocket chat endpoint."""



from backend.gateway.routes.chat import ConnectionManager


def test_connection_manager_init():
    """Test ConnectionManager initialization."""
    manager = ConnectionManager()
    assert manager.active_connections == {}


def test_connection_manager_disconnect_nonexistent():
    """Test disconnecting non-existent client doesn't raise."""
    manager = ConnectionManager()
    manager.disconnect("nonexistent")  # Should not raise
