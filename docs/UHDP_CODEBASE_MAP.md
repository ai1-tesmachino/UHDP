# UHDP Project Map

## 1. Purpose and product shape

UHDP is a hardware diagnostics and validation platform. At a high level it does four things:

- discovers local hardware and device metadata
- runs hardware diagnostics against those devices
- executes workflow-based validation sequences
- stores session and report artifacts as JSON files for later inspection

The repo is split into two major systems:

- Backend FastAPI service in `app/`
- Frontend React + TypeScript app in `frontend/`

Both are built around the same domain language: devices, diagnostics, sessions, workflows, reports, profiles.

---

## 2. Repository layout

### Root-level runtime and config

- `README.md` — minimal local startup notes
- `requirements.txt` — Python dependencies, including FastAPI, Pytest, APScheduler, Uvicorn
- `Dockerfile` — containerizes the backend with `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- `docker-compose.yml` — simple single-service container setup
- `.env` / `.env.example` — environment configuration overrides
- `data/` — runtime-generated state for sessions, reports, templates, and workflows
- `profiles/` — saved diagnostic profiles as JSON files

### Python backend

- `app/main.py` — app bootstrap and router registration
- `app/core/` — settings, logging, shared dependency injection helpers
- `app/api/` — HTTP endpoints by feature area
- `app/services/` — service layer for sessions and file-backed repositories
- `app/runtime/` — application lifecycle, job/task registry, plugin runtime, workflow runtime support
- `app/hal/` — hardware abstraction layer, diagnostics registry, executor, device abstraction
- `app/discovery/` — hardware/device discovery providers and registry
- `app/workflows/` — workflow engine, actions, templates, persistence, report generation
- `app/plugins/` — plugin loader, registry, system plugin integration
- `app/profiles/` — profile templates, repo, execution logic
- `app/reports/` and `app/workflows/reporting/` — report generation context and file handling
- `app/tests/` is actually the test suite under `tests/`

### Frontend

- `frontend/package.json` — Vite React project scripts
- `frontend/src/App.tsx` — app root with `BrowserRouter`
- `frontend/src/routes/index.tsx` — route map
- `frontend/src/pages/` — dashboard, device discovery, diagnostics, execution, results, report viewer
- `frontend/src/api/` — thin Axios wrappers over backend endpoints
- `frontend/src/components/` — shared layout pieces like sidebar/nav/status cards

---

## 3. Core backend architecture

### 3.1 Startup and runtime lifecycle

The backend entrypoint is `app/main.py`.

Important behavior:

- config is loaded from `app.core.config.get_settings()`
- logging is initialized via `setup_logging()`
- a FastAPI app is created with a lifespan hook
- during startup, `Application()` is instantiated and `await application.start()` runs
- the runtime is attached to `app.state.application` and `app.state.runtime`
- during shutdown, `await application.stop()` runs

This means the repo is built around a runtime container rather than a plain CRUD app. The runtime is configured in `app/runtime/context.py`, which registers:

- state manager
- event bus
- task manager
- job manager
- plugin registry / loader / manager
- workflow repository, execution repo, template repo
- validator and audit trail

The runtime lifecycle itself is implemented in `app/runtime/application.py` with `RuntimeStatus` transitions (`STOPPED`, `RUNNING`, `STOPPING`).

### 3.2 API composition

The API is split by feature area and included into the main app.

Key routers:

- `app/api/devices.py` — device discovery endpoints
- `app/api/routes/diagnostics.py` — diagnostic catalog and execution endpoints
- `app/api/sessions/routes.py` — general session CRUD-like routes
- `app/api/sessions/diagnostic_routes.py` — session-based diagnostic execution and report retrieval
- `app/api/router.py` — main combined router for health, sessions, workflows, diagnostics
- `app/api/plugins.py`, `app/api/profiles.py`, `app/api/reports.py`, `app/api/reports_export.py` — feature-specific passes

The FastAPI app registers routers in `app.main` and also in `app.api.router`.

### 3.3 Service and domain layer

The backend is not just raw route handlers. It organizes logic into layers:

- `app/services/` — orchestration and persistence layer for session objects and file-backed repositories
- `app/runtime/services/` — runtime services, including diagnostics execution support
- `app/discovery/` — machine discovery providers
- `app/hal/` — hardware abstraction and diagnostic execution
- `app/workflows/` — action-driven validation engine
- `app/plugins/` — runtime plugin mechanism

This layering is deliberate: route modules are thin adapters over domain services.

---

## 4. Device discovery and HAL model

### 4.1 Discovery system

The repo has a discovery subsystem in `app/discovery/`.

The important class is `DiscoveryService`:

- it owns a list of `DiscoveryProvider` implementations
- each provider discovers a specific class of hardware or system metadata
- results are aggregated into a `DiscoveryResult`
- devices are registered in a `DeviceRegistry`

This is how the app learns which devices are present locally. The discovery providers include CPU, memory, storage, display, system, motherboard, network, and battery discovery.

### 4.2 Hardware abstraction layer

The HAL layer is in `app/hal/` and provides the diagnostic core.

Key concepts:

- `DiagnosticRegistry` — maps a diagnostic key (e.g. `cpu`, `memory`, `storage`) to a `Diagnostic` instance
- `DiagnosticExecutor` — executes by diagnostic type
- `DiagnosticRequest` / `DiagnosticResult` — request/result model objects
- `DiagnosticStatus` — PASS/FAIL/ERROR/PENDING states
- `DeviceManager` + adapters — local device adapter abstraction

The default diagnostic catalog is registered in `app/hal/default_diagnostics.py` and includes:

- cpu
- memory
- storage
- network
- display
- battery
- webcam
- keyboard
- speaker
- usb
- usb_c
- hdmi
- vga
- wifi
- bluetooth
- system

This is a strong signal that the app is designed for hardware validation rather than generic web/backend logic alone.

---

## 5. Diagnostic workflow model

### 5.1 Diagnostic execution path

A typical backend diagnostic flow is:

1. frontend calls `/diagnostics/` or session routes
2. `DiagnosticService` constructs a `DeviceManager` and `DiagnosticExecutor`
3. `DiagnosticExecutor` looks up the named diagnostic in the registry
4. The specific `Diagnostic` instance runs against a device request
5. a `DiagnosticResult` is returned and summarized

The actual session-oriented flow is different and more complete:

- `DiagnosticSessionService.create_session()` creates a session and populates discovered devices
- `execute_diagnostic()` validates session and device existence, runs a single diagnostic, stores it in a `DiagnosticResultCollection`, updates summary
- `execute_workflow()` executes a generated workflow on a device, collects result objects, builds a report, persists session and report data

### 5.2 Workflow engine

The workflow system lives under `app/workflows/`.

Key pieces:

- `Workflow` — definition with `name` and `actions`
- `WorkflowEngine` — iterates actions and handles success/failure/stop conditions
- `WorkflowContext` — key/value object store for runtime variables
- `WorkflowResult` / `WorkflowStatus` — execution outcome
- `action.py` and `action_registry.py` — action abstraction
- `templates/full_system_validation_workflow.py` — generates a workflow based on selected diagnostics

The pattern is action-driven, not event-driven at the orchestration layer. Each action adds data to the workflow context, and a later step can fail the workflow if a result is negative.

Example: `create_full_system_validation_workflow()` builds a list of diagnostic actions such as `RunCpuDiagnosticAction`, `RunMemoryDiagnosticAction`, etc., then appends `FailIfDiagnosticFailedAction` after each one. This is a workflow-first validation pipeline.

---

## 6. Sessions, persistence, and reports

### 6.1 Session persistence

`app/services/session_service.py` manages in-memory session objects.

`app/services/file_session_repository.py` adds durable file persistence with JSON files stored under:

- `data/sessions/`
- file name pattern: `<session_id>.json`

The session repository serializes `datetime` values to ISO strings and stores session dictionaries as JSON. This is important because the runtime is built to persist diagnostics state to disk.

### 6.2 Report generation

The report path is mostly built from workflow results and context data.

`app/workflows/reporting/report_builder.py`:

- reads diagnostic result values from the workflow context
- collects result objects into a `DiagnosticResultCollection`
- builds a `DiagnosticReport`
- calculates overall status (PENDING / PASSED / FAILED / ERROR)
- stores `diagnostic_summary` in the report data

`FileReportRepository` and `FileSessionRepository` persist the generated report/session to disk. The data directories include:

- `data/reports/`
- `data/sessions/`
- `data/workflows/`
- `data/templates/`
- `data/executions/`

This file-based persistence makes the project feel like a desktop-oriented diagnostic platform with a local state store instead of a database-backed service.

---

## 7. Profiles and plugin architecture

### 7.1 Profiles

There are built-in profile JSON files under `profiles/`:

- `quick_test.json`
- `extended_test.json`
- `manufacturing_qa.json`
- `refurbishment_qa.json`
- `service_center_qa.json`

These are backed by `ProfileService`, which can create, list, delete, and execute named diagnostic profiles. The execution pattern is simple: load profile diagnostics, run each diagnostic against a device, and collect results.

This is a second important validation concept in the repo: named hardware test packs.

### 7.2 Plugins

`app/plugins/` implements a lightweight plugin system.

- `PluginLoader` loads a plugin module dynamically via `importlib`
- `PluginManager` initializes and registers plugin instances
- `PluginRegistry` stores loaded plugins
- `BasePlugin` defines plugin lifecycle (`initialize`, `shutdown`)

At startup, `RuntimeContext.start()` loads the system diagnostics plugin:

- `app.plugins.system.diagnostics.plugin`

The plugin exposes runtime diagnostics services and task services. This indicates the repository was designed to support modular runtime diagnostics, even if the current app still centers on local device execution.

---

## 8. Frontend architecture

The frontend is intentionally small and straightforward.

### Route map

The React app uses `react-router-dom` and defines these routes in `frontend/src/routes/index.tsx`:

- `/` → Dashboard
- `/devices` → DeviceDiscovery
- `/diagnostics` → DiagnosticSelection
- `/execution` → Execution
- `/results` → Results
- `/report` → ReportViewer

### Frontend API layer

`frontend/src/api/` has thin wrappers around backend endpoints:

- `client.ts` — Axios instance with `baseURL: http://localhost:8000`
- `health.ts` — health checks
- `devices.ts` — device list endpoints
- `diagnostics.ts` — diagnostic catalog and execution calls
- `sessions.ts` — session creation and workflow runs
- `reports.ts` — report retrieval

### App behavior

The dashboard loads health, device count, and available diagnostics in parallel using `Promise.allSettled`, which is a good example of the repo’s pragmatic UI style: it tolerates backend outage and still renders partial state.

The UI is not complex; it is orchestration-driven and designed to present hardware diagnostics status rather than deep business workflows.

---

## 9. Data and configuration conventions

Important repo conventions:

- config is environment-driven via `pydantic_settings` and `.env`
- default backend host/port is `0.0.0.0:8000`
- default data root is `data`
- CORS default origin is `http://localhost:3000`
- JSON files are the persistence format, not a relational database
- the repo uses session IDs and report IDs as UUID strings
- diagnostic status is modeled explicitly rather than using ad hoc booleans

This project has a desktop-like diagnostic architecture, not a microservice or database-heavy backend.

---

## 10. Test and validation footprint

The repo includes a Python pytest suite under `tests/`.

Key tests:

- `tests/test_health.py` validates the `/health/` endpoint
- `tests/test_sessions.py` exercises session creation and retrieval
- `tests/workflows/` and `tests/diagnostics/` cover workflow/diagnostic behavior
- `tests/plugins/`, `tests/profiles/`, `tests/reports/` validate domain subsystems

`app/pytest.ini` configures:

- `pythonpath = .`
- `testpaths = tests`
- `asyncio_mode = auto`

This is a good indicator that the project expects async and plugin-aware runtime tests to be present.

---

## 11. Architectural summary

The project’s mental model is:

- discover hardware
- register diagnostics
- orchestrate them via workflows
- persist sessions and report data to disk
- expose everything through FastAPI and a small React frontend

In practical terms, the repo is a local hardware-validation platform with layered runtime, diagnosis, and workflow code rather than a generic web application. Its strongest architecture pattern is a domain-driven but file-backed execution model.

The most important files to understand first are:

- `app/main.py`
- `app/runtime/context.py`
- `app/api/sessions/diagnostic_routes.py`
- `app/services/diagnostic_session_service.py`
- `app/hal/default_diagnostics.py`
- `app/workflows/templates/full_system_validation_workflow.py`
- `frontend/src/routes/index.tsx`

These files explain how the system turns hardware discovery into executed diagnostics and persisted reports.

# Future Work

M11:
- TBD

M12:
- TBD