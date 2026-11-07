---
name: UHDP Architecture
alwaysApply: true
---

# UHDP Architecture

UHDP is a local hardware diagnostics and validation platform. Its main workflow discovers devices, runs diagnostics or workflows, aggregates results, and stores sessions and reports.

## Backend

- The FastAPI application starts at `app.main:app`. Follow the existing `Application` and `RuntimeContext` lifecycle.
- HTTP endpoints live in feature modules under `app/api/`; router registration is centralized in `app/main.py` and `app/api/router.py`.
- Keep route handlers focused on HTTP orchestration. Put domain and runtime behavior in the existing layers: `app/services/`, `app/runtime/`, `app/hal/`, `app/discovery/`, `app/workflows/`, `app/profiles/`, and `app/plugins/`.
- Preserve the separation between local and cloud services. Do not merge responsibilities across `app/` and `cloud/`.

## Frontend

- The frontend is React, TypeScript, and Vite under `frontend/`.
- Routing is managed by `frontend/src/App.tsx` and `frontend/src/routes/`; pages belong in `frontend/src/pages/`.
- Reuse existing API wrappers under `frontend/src/api/` and shared UI under `frontend/src/components/`. Preserve backend request and response contracts.

## Persistence, runtime data, and tests

- Local persistence includes SQLite and file-backed session/report data. Treat `data/` and database files as operational state; never reset or remove them as part of routine changes or tests.
- Tests live in `tests/`; pytest settings are in `app/pytest.ini`. Use temporary or isolated data for tests.
- Read `docs/UHDP_CODEBASE_MAP.md` for orientation, then verify behavior against current source and tests because the map may lag implementation.

## Hardware and compatibility

- Hardware discovery and diagnostics run against the machine hosting the backend. Do not assume it is the target device.
- Inspect diagnostic behavior before execution. Get explicit approval before stress tests or potentially disruptive operations.
- Multiple diagnostic, report, and router paths may coexist. Trace usage and tests before consolidating or removing apparently duplicated code.
