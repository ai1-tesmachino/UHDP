# UHDP — Project Architecture and Engineering Guide

> **Purpose:** A living, code-oriented map of the UHDP hardware diagnostics and validation platform. Keep this document synchronized with the implementation as the project evolves.
>
> **Repository baseline:** `f442a9c` (`feat: expand hardware diagnostics and reporting`). This guide describes the checked-out source, not a claim that every planned subsystem is complete.

## 1. What the project does

UHDP is a local hardware diagnostics and validation application. Its main product flow is:

1. Discover hardware and system devices on the machine running the backend.
2. Select individual diagnostics or a named diagnostic profile.
3. Execute diagnostics directly or orchestrate them through a workflow.
4. Aggregate outcomes into a diagnostic summary and report.
5. Expose the workflow to a browser UI through a FastAPI backend.

The codebase contains two generations of some concepts (for example, diagnostics and reporting). Treat the flows described below as the current implementation and verify actual imports and router wiring before extending a similarly named legacy module.

## 2. System context

```text
Browser
  React + TypeScript + Vite
      │ Axios HTTP calls
      ▼
FastAPI application (app.main:app)
      ├── API routers
      ├── session/application services
      ├── discovery providers and device registry
      ├── diagnostic service → registry → executor → diagnostic implementation
      ├── workflow engine → ordered diagnostic actions → workflow context
      └── JSON repositories → sessions, reports, workflows, templates, executions
```

The frontend and backend are separate processes. The browser UI calls the backend at a URL currently hardcoded in `frontend/src/api/client.ts`; backend CORS and other settings are loaded from `app/core/config.py`.

## 3. Repository boundaries

| Area | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI construction, lifespan, CORS, and router inclusion |
| `app/core/` | Environment-backed settings, logging, and shared dependency helpers |
| `app/api/` | HTTP route handlers and router composition |
| `app/services/` | Session/report use cases and file-backed repositories |
| `app/discovery/` | Hardware discovery providers, results, and device registry |
| `app/hal/` | Hardware adapter boundary, diagnostic models/registry/executor, diagnostics, evaluation |
| `app/runtime/` | Runtime lifecycle, managers, event/job/task infrastructure, runtime services |
| `app/workflows/` | Workflow model/engine, actions, templates, persistence, report building |
| `app/plugins/` | Dynamic plugin loading, registration, lifecycle, and system diagnostics plugin |
| `app/profiles/` | Named diagnostic sets and file-backed profile repository |
| `app/reports/` | Report-generator/storage implementation alongside workflow reporting |
| `frontend/src/` | Browser entry point, routes, pages, components, API clients, types, WebSocket client |
| `tests/` | Pytest suites grouped by API and domain subsystem |
| `data/` | Local runtime output; not source-controlled application fixtures |
| `profiles/` | Built-in profile JSON definitions |

## 4. Backend startup and runtime lifecycle

`app.main:app` is the ASGI entry point (also used by the Docker image). At import/startup it reads settings and configures logging. FastAPI's lifespan function creates an `Application`, starts it, and exposes both application and runtime on `app.state`. Shutdown delegates to `Application.stop()`.

`app/runtime/application.py` wraps a `RuntimeContext` and tracks lifecycle status. `app/runtime/context.py` constructs the runtime components and file repositories, builds workflow services, registers objects in `RuntimeRegistry`, loads `app.plugins.system.diagnostics.plugin`, and starts the job manager. This is the intended composition point for runtime-managed dependencies; avoid creating parallel global runtime state.

The plugin system is small and explicit:

- `PluginLoader` imports a module and instantiates its `Plugin` class.
- `PluginManager` attaches the runtime, initializes the plugin, and registers it.
- `BasePlugin` defines initialize/shutdown lifecycle.
- The diagnostics plugin exposes runtime health/task services.

When changing startup, keep lifecycle ownership symmetrical: anything initialized at runtime start should have a deliberate shutdown path.

## 5. Discovery, hardware abstraction, and diagnostic execution

### Discovery

`app/discovery/discovery_service.py` owns discovery providers and a `DeviceRegistry`. Each provider returns discovered device models; the service clears/repopulates the registry and aggregates a `DiscoveryResult`. Existing providers cover categories such as CPU, memory, storage, display, system, motherboard, network, and battery. Additional provider modules exist, so use the registered provider list—not filenames alone—to determine active discovery behavior.

Discovery is local to the backend host. API calls such as listing devices trigger discovery rather than querying a remote inventory service.

### HAL diagnostics

The HAL's principal concepts are:

- `DiagnosticRegistry`: maps a string diagnostic key to an implementation.
- `DiagnosticRequest` and `DiagnosticResult`: execution input/output.
- `DiagnosticExecutor`: looks up and invokes a diagnostic.
- `DiagnosticStatus`: explicit result status values.
- adapters/device manager: boundary for local hardware interaction.
- evaluator and result collection: quality evaluation and aggregate counts.

`app/hal/default_diagnostics.py` constructs the default catalog, including CPU, memory, storage, network, display, battery, webcam, keyboard, speaker, USB/USB-C, HDMI, VGA, Wi-Fi, Bluetooth, and system diagnostics.

There is also a runtime-level diagnostic service at `app/runtime/services/diagnostic_service.py`. Before adding a new execution entry point, trace callers of both that service and `app/hal/diagnostic_service.py`; avoid exposing registry internals directly to route code.

## 6. Sessions and the main validation flow

The session-oriented orchestration is centered on `app/services/diagnostic_session_service.py` and its routes in `app/api/sessions/diagnostic_routes.py`.

### Create session

`POST /diagnostic-sessions/` creates a session through the session service, runs discovery, records the discovered device summaries, initializes diagnostic/workflow/report fields, and saves the result with `FileSessionRepository`.

### Execute a selected suite

The execute endpoint accepts a session ID, device ID, and selected diagnostic names. It builds a workflow using `app/workflows/templates/full_system_validation_workflow.py`, executes it through `WorkflowEngine`, gathers result values from the workflow context, builds a report, writes the report and session, and returns a response containing workflow/report summaries.

The workflow template maps diagnostic names to action classes and context result keys. The default list is CPU, memory, storage, and network. Validate requested names at the API/domain boundary: the template currently skips names it does not recognize.

### Execute one diagnostic or a profile

The session service also supports single-diagnostic and profile-based execution. Profiles live under `profiles/` as JSON; `ProfileService` loads a named profile and runs its diagnostics against a device.

### Session state and persistence

`SessionService` provides in-memory session creation, while `DiagnosticSessionService` maintains a process-local cache and uses `FileSessionRepository` for persisted session data. The repository stores files under the configured sessions directory (default `data/sessions/`). Reports and runtime workflow artifacts use additional JSON/file repositories under `data/reports/`, `data/executions/`, `data/workflows/`, and `data/templates/`.

Treat `data/` as generated local state. Tests that touch repositories should use temporary directories rather than checking generated machine data into source control.

## 7. Workflow engine and report construction

Workflows are ordered action sequences, not general-purpose DAGs. `WorkflowContext` is the mutable key/value store passed between actions. Diagnostic actions execute work and place result objects under known keys; failure-check actions can stop the sequence. `WorkflowEngine` converts workflow stop/failure exceptions into a `WorkflowResult` and status.

`ReportBuilder` reads recognized result keys from the context, builds a `DiagnosticResultCollection`, calculates an aggregate status, and creates a `DiagnosticReport`. `FileReportRepository` persists workflow reports. The repository also contains a separate `app/reports/` generator/storage family: inspect route imports and call sites before assuming it is the same report pipeline.

## 8. HTTP API and route composition

`app/main.py` includes routers directly and also includes the aggregate router in `app/api/router.py`. The aggregate router itself includes feature routers. This creates overlap for some routes (notably devices and diagnostic sessions); verify `app.routes` and OpenAPI output when editing registrations, and avoid adding a path in two places.

Feature endpoints are implemented across:

- `app/api/devices.py` — discovery/list and single-device lookup
- `app/api/routes/diagnostics.py` — catalog and direct diagnostic execution
- `app/api/sessions/` — general and diagnostic session routes
- `app/api/profiles.py` — profile operations
- `app/api/reports.py` and `app/api/reports_export.py` — report access/export
- health, workflow, plugin, and WebSocket modules under `app/api/`

The frontend/backend contract is not uniformly centralized. For any API change, check the matching frontend wrapper and route/test coverage; in particular, compare HTTP method, URL path, query parameters, and JSON body shape.

## 9. Frontend

The browser app starts at `frontend/src/main.tsx`, mounts `App`, and wraps the UI in `BrowserRouter`. `frontend/src/routes/index.tsx` maps `/`, `/devices`, `/diagnostics`, `/execution`, `/results`, and `/report` to page components.

The pages are under `frontend/src/pages/`; shared navigation/layout is under `frontend/src/components/`. `frontend/src/api/` contains thin Axios wrappers and `frontend/src/types/` contains TypeScript domain types. The Dashboard loads health, devices, and diagnostics concurrently and tolerates individual request failures.

The API base URL is currently hardcoded to `http://localhost:8000`. Vite's configured dev port, backend CORS origins, and this URL should be kept aligned when changing local or deployment configuration.

## 10. Configuration, run, and test

Configuration uses `pydantic-settings` in `app/core/config.py`, reads `.env`, and ignores extra environment keys. Important settings include application name/version, host/port, log level, data directories, CORS origins, and device/WebSocket intervals. Do not publish `.env`; use `.env.example` for safe configuration documentation.

Backend:

```powershell
.\.venv\Scripts\activate
uvicorn app.main:app --reload
pytest
pytest tests\api\test_diagnostic_session_routes.py -q
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
npm run build
```

Pytest configuration is in `app/pytest.ini`. `frontend/package.json` currently defines dev/build/preview scripts but no dedicated lint or test script.

## 11. Architectural cautions and next improvements

These are code-level observations to revisit as changes land, not a mandate for a rewrite:

1. **Consolidate route ownership.** Router inclusion currently overlaps between the application and aggregate router.
2. **Keep API contracts synchronized.** Frontend wrappers and backend paths/payloads have separate definitions; integration tests should cover the browser-facing shapes.
3. **Choose clear service boundaries.** There are multiple diagnostic/session/report paths. Establish one public use-case boundary per operation rather than routing through private fields or duplicate services.
4. **Make persisted shapes explicit.** Avoid converting domain objects to strings in JSON storage if callers must reconstruct and operate on them after restart. Define serialization schemas and round-trip tests.
5. **Close runtime lifecycles.** Ensure plugin shutdown is invoked when the runtime stops and cover startup/shutdown with tests.
6. **Make selection semantics explicit.** Distinguish an omitted diagnostic selection (use defaults) from an empty selection (run none or reject), and reject unsupported names rather than silently skipping them.
7. **Move long-running work behind jobs when needed.** The runtime already has job/task infrastructure; use it for lengthy diagnostics only after execution state transitions and progress delivery are clearly defined.
8. **Keep generated artifacts out of Git.** Dependencies, build output, caches, and runtime sessions/reports/executions are ignored. Preserve source, tests, built-in profile definitions, and intentional fixtures.

## 12. Updating this guide

When architecture changes, update the relevant section with the owning code path and a test or route that confirms it. Prefer recording current behavior and clearly labeling known inconsistencies over describing intended design as if it already exists. Keep this guide free of credentials, local device inventory, generated reports, and environment-specific secrets.
