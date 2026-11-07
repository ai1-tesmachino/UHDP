# Existing Phase 2 Work Preservation Record

- **Recorded:** 2026-11-06
**Branch/HEAD:** `main` / `30d66480eac01d0d7bbef5f671da0348853b7684`

All changes below were present before this Phase 1 closure pass. They are
uncommitted, unstaged, and must be preserved. No Phase 2 source or test file
was edited for Phase 1 during this pass.

## Modified tracked files

```text
app/api/dependencies.py
app/api/websocket/__init__.py
app/api/websocket/routes.py
app/core/dependencies.py
app/main.py
app/runtime/application.py
app/runtime/background/task_manager.py
app/runtime/context.py
app/runtime/events/event.py
app/runtime/events/event_bus.py
app/runtime/events/subscriptions.py
app/runtime/managers/job_manager.py
app/runtime/managers/state_manager.py
app/runtime/models.py
app/runtime/models/__init__.py
app/runtime/models/event.py
app/runtime/models/status.py
app/runtime/registry.py
app/websocket/bridge.py
app/websocket/manager.py
tests/runtime/test_application_failure.py
```

`app/runtime/models.py` contains a newline-only change; it has no functional
runtime change.

## Untracked Phase 2 files

```text
app/api/runtime.py
app/runtime/models/runtime.py
app/runtime/scheduler/async_scheduler.py
tests/runtime/test_core_components.py
tests/runtime/test_event_bus_async.py
tests/runtime/test_managed_execution.py
tests/runtime/test_runtime_api.py
tests/runtime/test_websocket_integration.py
```

The tracked diff at inspection was 937 insertions and 280 deletions across 21
files. No files were staged.

## Existing implementation represented by this work

The uncommitted work implements the Phase 2 runtime-core slice: runtime models
and statuses, component registry, state management, event bus and subscriptions,
job/background task management, asynchronous scheduler integration,
`RuntimeContext` lifecycle/bootstrap, dependency wiring, application startup,
WebSocket event bridging/routes, and runtime monitoring API. The eight untracked
files include the runtime API/models/scheduler and focused runtime tests.

The current backend test run passed with these changes present (529 passed,
45 warnings); that is regression evidence for this checkout, not a Phase 2 or
Phase 1 acceptance claim. The previous task also recorded a successful frontend
build. This preservation task does not complete, refactor, commit, or claim
acceptance of Phase 2.

## Phase 1 overlap boundary

| Existing Phase 2 area | Relationship to Phase 1 | Preservation rule |
|---|---|---|
| `app/main.py`, `app/runtime/application.py` | Application lifecycle and API registration affect all application routes | Do not replace startup/lifespan wiring to address a diagnostic issue |
| `app/runtime/context.py`, `app/api/dependencies.py`, `app/core/dependencies.py` | Runtime dependencies and workflow services are used by runtime APIs; session/workflow execution is also part of Phase 1 | Inspect exact call sites before any approved overlap change; retain runtime services and registrations |
| `app/api/websocket/*`, `app/websocket/*` | WebSocket routes and event bridge are runtime/API surface changes | Do not remove or rewrite as unrelated to diagnostic result fixes |
| `app/runtime/events/*`, `app/runtime/managers/*`, `app/runtime/background/*`, `app/runtime/scheduler/*`, runtime models/registry | Runtime infrastructure; the existing `DiagnosticJobService` is a separate service and was not replaced by `JobManager` | Preserve both systems; do not conflate or merge them during Phase 1 stabilization |
| `app/api/runtime.py` and `tests/runtime/*` | New runtime monitoring endpoint and Phase 2-specific coverage | Keep intact; no Phase 1 scope expansion |

If a Phase 1 fix later requires an overlapping file, make the smallest approved
change against its current content, preserve the existing Phase 2 behavior and
tests, and review the resulting diff before validation. Do not stash, reset,
discard, stage, commit, or overwrite this work without separate explicit
authorization.
