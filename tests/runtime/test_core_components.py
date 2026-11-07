from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.runtime.models.event import RuntimeEvent
from app.runtime.models.runtime import RuntimeJob
from app.runtime.models.status import JobStatus, RuntimeStatus
from app.runtime.registry import RuntimeRegistry
from app.runtime.managers.state_manager import StateManager


def test_runtime_models_use_utc_and_serialize():
    event = RuntimeEvent(event_type="runtime.started", source="test")
    job = RuntimeJob(job_type="maintenance")

    assert event.timestamp.tzinfo == UTC
    assert job.created_at.tzinfo == UTC
    assert event.model_dump(mode="json")["event_id"]
    assert job.model_dump(mode="json")["status"] == "pending"

    with pytest.raises(ValidationError):
        RuntimeJob(job_type="invalid", status="unknown")
    with pytest.raises(ValidationError):
        RuntimeJob(job_type="maintenance", created_at=datetime.now())

    assert RuntimeStatus.FAILED.value == "failed"
    assert JobStatus.TIMED_OUT.value == "timed_out"


def test_registry_registration_errors_and_component_listing():
    registry = RuntimeRegistry()
    component = object()
    registry.register("service", component)

    assert registry.get("service") is component
    assert registry.exists("service")
    assert registry.list_components() == ["service"]
    with pytest.raises(ValueError, match="already registered"):
        registry.register("service", object())
    with pytest.raises(KeyError, match="not found"):
        registry.get("missing")

    registry.unregister("unknown")
    registry.clear()
    assert registry.list_components() == []


def test_state_manager_copies_nested_values_and_updates_atomically():
    state = StateManager()
    source = {"nested": [1]}
    state.set("runtime:sample", source)
    source["nested"].append(2)
    returned = state.get("runtime:sample")
    returned["nested"].append(3)

    assert state.get("runtime:sample") == {"nested": [1]}
    assert state.exists("runtime:sample")
    state.update("runtime:sample", {"nested": [4]})
    assert state.get_all() == {"runtime:sample": {"nested": [4]}}
    with pytest.raises(KeyError):
        state.update("missing", 1)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda value: state.set(str(value), value), range(100)))
    assert len(state.get_all()) == 101
    state.delete("runtime:sample")
    state.clear()
    assert state.get_all() == {}
