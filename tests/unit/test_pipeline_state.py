"""Unit tests for PipelineState TypedDict and reducer patterns."""

from __future__ import annotations

from datetime import datetime, timezone


from backend.pipeline.state import PipelineState


def test_pipeline_state_creation():
    """Test creating a valid PipelineState."""
    state: PipelineState = {
        "design": {"name": "test", "agents": []},
        "current_step": 0,
        "max_steps": 50,
        "timeout_seconds": 300,
        "agent_results": [],
        "errors": [],
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "cost_total": 0.0,
        "current_agent": "",
        "output": "",
    }

    assert state["design"]["name"] == "test"
    assert state["current_step"] == 0
    assert state["max_steps"] == 50
    assert state["timeout_seconds"] == 300
    assert state["agent_results"] == []
    assert state["errors"] == []
    assert state["status"] == "pending"
    assert state["cost_total"] == 0.0
    assert state["current_agent"] == ""
    assert state["output"] == ""


def test_agent_results_accumulation():
    """Test that agent_results can accumulate via reducer pattern."""
    state: PipelineState = {
        "design": {"name": "test"},
        "current_step": 0,
        "max_steps": 50,
        "timeout_seconds": 300,
        "agent_results": [],
        "errors": [],
        "status": "running",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "cost_total": 0.0,
        "current_agent": "agent1",
        "output": "",
    }

    # Simulate adding results (as LangGraph reducer would do)
    result1 = {
        "agent_name": "agent1",
        "role": "collector",
        "content": "data collected",
        "tokens_used": 100,
        "cost_estimate": 0.01,
        "duration_seconds": 1.5,
        "status": "success",
        "error": None,
    }

    result2 = {
        "agent_name": "agent2",
        "role": "analyzer",
        "content": "data analyzed",
        "tokens_used": 200,
        "cost_estimate": 0.02,
        "duration_seconds": 2.5,
        "status": "success",
        "error": None,
    }

    # Manual accumulation (LangGraph does this automatically)
    state["agent_results"] = state["agent_results"] + [result1]
    assert len(state["agent_results"]) == 1
    assert state["agent_results"][0]["agent_name"] == "agent1"

    state["agent_results"] = state["agent_results"] + [result2]
    assert len(state["agent_results"]) == 2
    assert state["agent_results"][1]["agent_name"] == "agent2"


def test_errors_accumulation():
    """Test that errors can accumulate via reducer pattern."""
    state: PipelineState = {
        "design": {"name": "test"},
        "current_step": 0,
        "max_steps": 50,
        "timeout_seconds": 300,
        "agent_results": [],
        "errors": [],
        "status": "running",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "cost_total": 0.0,
        "current_agent": "agent1",
        "output": "",
    }

    # Simulate adding errors
    state["errors"] = state["errors"] + ["Error 1: Connection failed"]
    assert len(state["errors"]) == 1

    state["errors"] = state["errors"] + ["Error 2: Timeout"]
    assert len(state["errors"]) == 2
    assert "Connection failed" in state["errors"][0]
    assert "Timeout" in state["errors"][1]


def test_state_status_transitions():
    """Test valid status transitions."""
    state: PipelineState = {
        "design": {"name": "test"},
        "current_step": 0,
        "max_steps": 50,
        "timeout_seconds": 300,
        "agent_results": [],
        "errors": [],
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "cost_total": 0.0,
        "current_agent": "",
        "output": "",
    }

    # pending -> running
    state["status"] = "running"
    assert state["status"] == "running"

    # running -> completed
    state["status"] = "completed"
    assert state["status"] == "completed"

    # Test failure status
    state["status"] = "failed"
    assert state["status"] == "failed"

    # Test timeout status
    state["status"] = "timeout"
    assert state["status"] == "timeout"


def test_cost_accumulation():
    """Test that cost_total can accumulate."""
    state: PipelineState = {
        "design": {"name": "test"},
        "current_step": 0,
        "max_steps": 50,
        "timeout_seconds": 300,
        "agent_results": [],
        "errors": [],
        "status": "running",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "cost_total": 0.0,
        "current_agent": "",
        "output": "",
    }

    # Accumulate costs
    state["cost_total"] += 0.01
    assert state["cost_total"] == 0.01

    state["cost_total"] += 0.02
    assert state["cost_total"] == 0.03


def test_step_counter():
    """Test current_step incrementing."""
    state: PipelineState = {
        "design": {"name": "test"},
        "current_step": 0,
        "max_steps": 50,
        "timeout_seconds": 300,
        "agent_results": [],
        "errors": [],
        "status": "running",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "cost_total": 0.0,
        "current_agent": "",
        "output": "",
    }

    # Increment steps
    for i in range(1, 6):
        state["current_step"] = i
        assert state["current_step"] == i

    # Check max_steps boundary
    assert state["current_step"] < state["max_steps"]
