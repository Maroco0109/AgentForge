"""Tests for CollectorNode with Data Collector HTTP integration."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.pipeline.agents.collector import CollectorNode


def _make_state(source_hints=None, agents=None):
    """Create a minimal PipelineState for testing."""
    design = {
        "name": "Test Pipeline",
        "description": "Test description",
        "agents": agents or [],
        "source_hints": source_hints or [],
    }
    return {
        "design": design,
        "current_step": 0,
        "max_steps": 50,
        "timeout_seconds": 300,
        "agent_results": [],
        "errors": [],
        "status": "running",
        "start_time": "2024-01-01T00:00:00Z",
        "cost_total": 0.0,
        "current_agent": "",
        "output": "",
    }


def _make_collector():
    """Create a CollectorNode for testing."""
    return CollectorNode(
        name="test_collector",
        role="collector",
        description="Test data collector",
        llm_model="gpt-4o-mini",
    )


class TestCollectorNodeURLExtraction:
    """Test source URL extraction logic."""

    def test_extract_url_from_source_hints(self):
        node = _make_collector()
        state = _make_state(source_hints=["https://example.com/data"])
        url = node._extract_source_url(state)
        assert url == "https://example.com/data"

    def test_extract_url_from_agent_description(self):
        node = _make_collector()
        agents = [{"description": "Collect from https://example.com/api endpoint"}]
        state = _make_state(agents=agents)
        url = node._extract_source_url(state)
        assert url == "https://example.com/api"

    def test_no_url_returns_none(self):
        node = _make_collector()
        state = _make_state()
        url = node._extract_source_url(state)
        assert url is None

    def test_non_url_hints_ignored(self):
        node = _make_collector()
        state = _make_state(source_hints=["naver_shopping", "local_file"])
        url = node._extract_source_url(state)
        assert url is None


class TestCollectorNodeFallback:
    """Test LLM fallback when no source URL."""

    @pytest.mark.asyncio
    async def test_no_url_falls_back_to_llm(self):
        """When no source URL, should use parent LLM-based execution."""
        node = _make_collector()
        state = _make_state()

        with patch.object(
            node.router,
            "generate",
            new_callable=AsyncMock,
        ) as mock_generate:
            mock_generate.return_value = AsyncMock(
                content="Collection plan: gather data from web sources",
                usage={"total_tokens": 100},
                cost_estimate=0.001,
            )
            result = await node.execute(state)

        assert "agent_results" in result
        assert result["agent_results"][0]["status"] == "success"


class TestCollectorNodeHTTP:
    """Test HTTP integration with Data Collector service."""

    @pytest.mark.asyncio
    async def test_successful_collection(self):
        """Test full collection flow: create -> compliance -> collect -> data."""
        node = _make_collector()
        state = _make_state(source_hints=["https://example.com"])

        mock_responses = [
            # POST /collections
            AsyncMock(status_code=200, json=lambda: {"id": "col-123"}),
            # GET /compliance
            AsyncMock(status_code=200, json=lambda: {"status": "allowed"}),
            # POST /collect
            AsyncMock(status_code=200, json=lambda: {"status": "collecting"}),
            # GET /data
            AsyncMock(
                status_code=200,
                json=lambda: {"total_items": 5, "items": [{"text": "item"}]},
            ),
        ]
        # Add raise_for_status that does nothing
        for resp in mock_responses:
            resp.raise_for_status = lambda: None

        with patch("backend.pipeline.agents.collector.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(
                side_effect=[mock_responses[0], mock_responses[2]]
            )
            client_instance.get = AsyncMock(
                side_effect=[mock_responses[1], mock_responses[3]]
            )
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await node.execute(state)

        assert result["agent_results"][0]["status"] == "success"
        assert "Data collected" in result["agent_results"][0]["content"]

    @pytest.mark.asyncio
    async def test_compliance_blocked(self):
        """Test collection blocked by compliance check."""
        node = _make_collector()
        state = _make_state(source_hints=["https://blocked.com"])

        mock_responses = [
            # POST /collections
            AsyncMock(status_code=200, json=lambda: {"id": "col-456"}),
            # GET /compliance - blocked
            AsyncMock(
                status_code=200,
                json=lambda: {"status": "blocked", "reason": "robots.txt disallows"},
            ),
        ]
        for resp in mock_responses:
            resp.raise_for_status = lambda: None

        with patch("backend.pipeline.agents.collector.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_responses[0])
            client_instance.get = AsyncMock(return_value=mock_responses[1])
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await node.execute(state)

        assert result["agent_results"][0]["status"] == "failed"
        assert "blocked" in result["agent_results"][0]["error"].lower()

    @pytest.mark.asyncio
    async def test_connect_error_falls_back_to_llm(self):
        """Test connection error falls back to LLM mode."""
        import httpx

        node = _make_collector()
        state = _make_state(source_hints=["https://example.com"])

        with patch("backend.pipeline.agents.collector.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            # Also mock the LLM fallback
            with patch.object(
                node.router, "generate", new_callable=AsyncMock
            ) as mock_generate:
                mock_generate.return_value = AsyncMock(
                    content="Fallback plan",
                    usage={"total_tokens": 50},
                    cost_estimate=0.001,
                )
                result = await node.execute(state)

        assert result["agent_results"][0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test timeout returns failed result."""
        import httpx

        node = _make_collector()
        state = _make_state(source_hints=["https://slow.example.com"])

        with patch("backend.pipeline.agents.collector.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(
                side_effect=httpx.TimeoutException("Read timed out")
            )
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await node.execute(state)

        assert result["agent_results"][0]["status"] == "failed"
        assert "timed out" in result["agent_results"][0]["error"].lower()
