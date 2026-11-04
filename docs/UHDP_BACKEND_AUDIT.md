# UHDP Backend Audit — Phase 0

**Audit date:** 2026-11-04  
**Repository:** `ai1-tesmachino/UHDP`  
**Branch / baseline:** `main`, `70e96983473669ceea092371a6a507549da9c0ab`  
**Scope:** Checked-out backend, its active frontend API callers, tests, persistence configuration, and Linux launchers.

## Audit status and method

This is a Phase 0 audit only. No application code, dependencies, schemas, launchers, or frontend files were changed. The worktree was already dirty at audit start: 14 tracked files had modifications and there were untracked skill files, `app/diagnostics/display_tests.py`, and `frontend/src/diagnostics/`. Those changes were preserved; findings describe the checked-out source, including those changes.

The Codebase Memory index was recorded at `2026-11-04T08:28:19Z`, before the current worktree state. Its graph and coverage were used for navigation only; the findings below were checked against local source. Coverage returned no recorded issue for cited files but marked their metadata changed. Ignored cache directories were outside the source audit.

One focused test was run with temporary file-backed storage:

```text
pytest tests/api/test_diagnostic_session_routes.py::test_execute_single_diagnostic -q
FAILED: expected status "completed", received "checks_complete"
```

The temporary test data was removed. The full backend suite, Linux launchers, Linux Live image, and physical hardware were not run or validated.

## A. Current backend architecture

### Startup and API composition

`app.main:app` creates an `Application` during FastAPI lifespan startup, starts the runtime, and starts `SyncWorker` only when `STORAGE_BACKEND=sqlite`. Shutdown stops the storage benchmark service, sync worker, and runtime (`app/main.py`). `RuntimeContext` constructs the APScheduler-backed runtime job manager and JSON workflow/execution/template repositories (`app/runtime/context.py`).

`app/main.py` mounts the direct diagnostics router and `app.api.router`. The aggregate router mounts device discovery, diagnostic-session, health, session, and workflow routes. Reports, report exports, profiles, diagnostic jobs, evidence, sync, and storage-benchmark routers are mounted separately. The active direct diagnostic endpoint is in `app/api/routes/diagnostics.py`. `app/api/diagnostics.py` and `app/api/diagnostic_sessions.py` contain older similarly named routers, but are not imported by `app.main` or `app.api.router`; do not treat them as currently mounted routes.

### Active diagnostic execution paths

| Entry point | Current path | Evaluation and persistence |
|---|---|---|
| `POST /diagnostics/{diagnostic_type}` | `app/api/routes/diagnostics.py` → `app.runtime.services.diagnostic_service.DiagnosticService` → `app.hal.diagnostic_service.DiagnosticService` → `DiagnosticExecutor` → registered diagnostic | Returns the raw result. Does not evaluate or persist it in a QC session. |
| `POST /diagnostic-sessions/{session_id}/diagnostics/{device_id}/{diagnostic_type}` | `app/api/sessions/diagnostic_routes.py` → `DiagnosticSessionService.execute_diagnostic` → runtime/HAL diagnostic service → `DiagnosticEvaluator` | Adds a result and `TestResultRecord` to the session, refreshes the report, and saves through the configured session/report repositories. |
| `POST /diagnostic-sessions/{session_id}/execute` | Route creates a `full_system_validation_workflow` → `DiagnosticSessionService.execute_workflow` → `WorkflowEngine` → workflow action classes → HAL service | Workflow actions execute diagnostics, but do not call `DiagnosticEvaluator`. The session service collects results and builds/saves a report through a different path. |
| `POST /profiles/{name}/execute` | `app/api/profiles.py` → `DiagnosticSessionService.execute_profile` → `ProfileService.execute_profile` → runtime/HAL service | Evaluates each result in the session service and stores it in the session/report. |
| `POST /diagnostic-jobs/` | `DiagnosticJobService` → private `_execute_test` dispatch, specialized stress/battery routines, and a direct `MemoryStressDiagnostic` call | Has its own execution statuses/evaluator and per-job JSON persistence; optionally attaches the job to a session as a performance result. It does not use the normal diagnostic session execution path. |

The active paths share some HAL implementations, but they do not share one orchestration/evaluation/persistence pipeline. A separate APScheduler `JobManager` exists in the runtime; diagnostic jobs instead use their own `ThreadPoolExecutor`.

### Discovery and hardware abstraction

`DiscoveryService` runs the registered CPU, memory, storage, display, system, motherboard, network, battery, GPU, and peripheral providers, clears the in-memory registry, then registers the new results (`app/discovery/discovery_service.py`). `DeviceRegistry` is keyed by `device_id`. A `Device` carries only `device_id`, `device_type`, `name`, and `properties` (`app/discovery/models/device.py`). The HAL `LocalAdapter` returns host metadata and assigns a new UUID whenever `discover_device()` is called (`app/hal/adapters/local_adapter.py`).

The platform-specific discovery and diagnostic providers are worth retaining. Linux inventory code has substantial provider/test coverage; Windows utilities such as `app/hal/diagnostics/windows_utils.py` also exist. However, the HAL adapter itself is only a local-host metadata adapter, not an OS-specific adapter family. The capability catalog is separate from the diagnostic registry and primarily reports component/tool availability.

### Session, QC, and reports

`DiagnosticSessionService` owns session orchestration, its in-process cache, manual checks, cosmetic inspection, display-test attempts, retest histories, technician records, report refresh, and profile/workflow calls. Session IDs are UUIDs created by `SessionService`; `device_id` remains the principal hardware identifier in requests and stored records.

`ReportBuilder` in `app/workflows/reporting` creates a `DiagnosticReport` from workflow-context result keys. A separate generator/model/storage family exists under `app/reports`. The active `/reports` endpoints use repository factories; `/reports/export` uses `ReportService` and the separate report-storage interface. JSON and HTML export are present, but report identity/finalization rules are not unified across these families.

### Persistence, evidence, jobs, and dependencies

`app.core.config.Settings` defaults to `STORAGE_BACKEND="file"`, `DATA_DIR="data"`, and supports `file`, `sqlite`, or `supabase`. The regular Linux launcher chooses a persistent XDG state directory and defaults to SQLite, importing legacy JSON sessions/reports on startup. The Live launcher requires a removable ext4 `UHDP_DATA` partition, sets `DATA_DIR`, `REPORTS_DIRECTORY`, and `SESSIONS_DIRECTORY` under its persistent directory, and binds the API/UI to loopback. It does not set `STORAGE_BACKEND`; the Live build copies `app`, `profiles`, requirements, frontend assets, and launch scripts, but not `.env`, so the packaged default is file storage unless the runtime environment overrides it. `docs/LINUX_LIVE_USB.md` explicitly states that the Live build/launcher and physical-device behavior have not been validated.

SQLite uses the standard-library `sqlite3` module. `SQLiteDatabase.connection()` enables foreign keys, a 30-second busy timeout, and `synchronous=FULL`; initialization enables WAL. Each repository operation uses a connection context that commits on success and rolls back on exceptions. SQL migrations are applied transactionally and recorded by full filename. The schema stores session/report JSON payloads alongside selected normalized rows, revisions, audit events, evidence metadata, and a cloud outbox.

Evidence uses `EvidenceStorage` and SQLite metadata. It writes files through a temporary file, computes SHA-256, stores the file under `DATA_DIR/Evidence`, and verifies the checksum on retrieval. The evidence API rejects non-SQLite storage configuration.

`requirements.txt` already includes Pydantic v2, `pydantic-settings`, `psutil`, FastAPI, and APScheduler. No `pyproject.toml` or separate `requirements-dev.txt` was present at the repository root.

## B. Problems ranked by severity

Priority is product/release impact, not a security rating. **P1** blocks dependable QC certification; **P2** is important reliability/maintainability work; **P3** is documentation/cleanup.

### P1-1 — Execution, evaluation, and result contracts diverge

**Evidence:** `app/api/routes/diagnostics.py:28-44`; `app/services/diagnostic_session_service.py:633-698,1269-1372,1374-1472`; `app/workflows/actions/diagnostics/run_cpu_diagnostic_action.py`; `app/services/diagnostic_job_service.py:251-280,628-710`; `app/hal/diagnostic_executor.py:23-61`.

**Existing behavior:** The session single-test path evaluates and persists a result. The profile path also evaluates results. The direct diagnostics route returns a raw result without session evaluation/persistence. Workflow diagnostic actions call the HAL service directly; `execute_workflow` collects those results without applying `DiagnosticEvaluator`. Diagnostic jobs implement their own dispatch, status mapping, criteria evaluation, and JSON persistence.

**Why it is a problem:** The same diagnostic can acquire different status/result shapes and persistence behavior depending on its entry point. Workflow reports may contain unevaluated results, while profile/session reports may contain evaluated results. This does not satisfy the required canonical execution pipeline.

**Proposed correction:** Keep the existing diagnostic implementations and registry. Establish one service-level execution operation that owns request validation, execution, evaluation, run/result persistence, and standardized status mapping. Route direct, session, profile, workflow-action, and job execution through it; keep job-specific scheduling/progress/cancellation as an adapter around that operation.

**Change risk:** High fan-in: route response consumers, workflow stop/fail conditions, profiles, job result consumers, and existing reports may depend on current status fields. Preserve raw status and legacy response fields during migration.

**Tests required:** For the same diagnostic fixture, assert identical run identity, execution/evaluation outcomes, and persisted result through direct, session, profile, workflow, and job entry points. Cover unsupported, failed, errored, cancelled, and inconclusive outcomes.

### P1-2 — Physical asset, component, and run identities are not canonical

**Evidence:** `app/discovery/models/device.py`; `app/discovery/discovery_service.py:51-65`; `app/hal/adapters/local_adapter.py`; `app/hal/diagnostic_request.py`; `app/hal/diagnostic_result.py`; `app/diagnostics/models/test_result.py`; `app/persistence/local/migrations/0002_domain_evidence.sql:8-45`; `app/persistence/local/database.py:843-905`; `app/api/sessions/diagnostic_routes.py:108-130`.

**Existing behavior:** There is no `asset_id` or `component_id` domain field in the inspected application/schema. Intake accepts `asset_tag`, but session/device persistence centers on `device_id`. `Device` has no stable component identity fields. Discovery clears and reconstructs its registry; several providers use category identifiers and others use device/index-derived identifiers. `LocalAdapter` generates a fresh UUID on each device discovery. Workflow actions call `get_device()` independently rather than using the requested session `device_id`, so each result can be associated with an unrelated fresh adapter UUID. `DiagnosticResult.diagnostic_id` is persisted into the SQLite `diagnostic_runs.run_id` column, while `TestResultRecord` creates a separate `run_id`.

**Why it is a problem:** One `device_id` currently represents host identity, discovered category/component, and session target in different paths. There is no reliable asset/component match across discovery refreshes, and diagnostic result, test-result, and evidence run references can disagree.

**Proposed correction:** Introduce separate asset, component, session, run, report, and evidence identities while treating existing `device_id` values as a compatibility mapping. Define component matching/conflict rules and ensure every execution path receives the session's resolved asset/component IDs. Keep uncertain matches explicit; do not auto-promote serial numbers or category labels into physical asset identity.

**Change risk:** Data backfill is inherently uncertain: historical `device_id` values do not always identify a unique physical asset or component. Existing frontend/API callers use `device_id`; translate compatibly and do not silently rewrite prior records.

**Tests required:** Repeated discovery does not duplicate stable components; ambiguous matches are reported; duplicate/missing serials do not merge assets; workflow run records use the selected session target; manual and automated run IDs can be linked to evidence; old `device_id` payloads still round-trip.

### P1-3 — QC completion/finalization is incomplete and is not enforced as immutable

**Evidence:** `app/services/diagnostic_session_service.py:700-751,753-850,1100-1118`; `app/api/sessions/diagnostic_routes.py:428-475,741-753`; `tests/api/test_diagnostic_session_routes.py:138`.

**Existing behavior:** `complete_session()` sets status to `checks_complete`; `finalize_session()` checks only that `final_disposition` is one of five allowed strings before setting `completed`. `update_technician_record()` sets `qa_approved_at` whenever a disposition is supplied, even when no approver identity is provided or validated. Several write operations, including intake/manual result/diagnostic execution/technician updates, do not reject completed sessions. Cosmetic and display-specific operations do have their own completed-session guard. Reopening clears disposition/QA fields and returns the same session to `checks_complete`.

**Why it is a problem:** There is no single completion validator or consistent read-only boundary, and a free-form technician record is treated as approval. A finalized QC record can be modified through unguarded write paths. Also, the existing focused API test currently fails: it expects `"completed"` from `/complete`, while the service returns `"checks_complete"`.

**Proposed correction:** Define explicit QC lifecycle transitions and completion rules (planned diagnostics/manual checks, display/cosmetic requirements, disposition, approval actor). Enforce editability centrally for all mutations; require explicit authorized reopen/retest and preserve original finalized snapshots. Resolve the `/complete` contract deliberately rather than simply changing the assertion.

**Change risk:** Frontend workflow logic and reports distinguish statuses and may depend on current retest behavior. Test transitions and legacy statuses before changing the contract.

**Tests required:** Fix the observed status mismatch with an agreed lifecycle contract; test incomplete completion rejection, missing approver rejection, all post-finalization mutations, authorized reopen, and preservation of the finalized report and earlier runs.

### P1-4 — Report identity changes on refresh and finalization does not freeze report content

**Evidence:** `app/workflows/reporting/report_builder.py:52-89`; `app/services/diagnostic_session_service.py:1029-1098,1269-1372`; `app/persistence/local/repositories.py:32-88`; `app/persistence/local/database.py:256-327`; `app/persistence/local/migrations/0001_local_records.sql:18-35`.

**Existing behavior:** Every `ReportBuilder.build()` assigns a new UUID and timestamp. `_refresh_report()` rebuilds and saves on session updates, while repositories store the latest report under a session-derived key such as `diagnostic_<session_id>`. SQLite appends report revision snapshots, but the latest payload remains mutable and the revision ID is not part of the API contract. File report storage overwrites JSON/HTML files. `execute_workflow()` builds a separate, less-enriched report than `_refresh_report()`. No report checksum/verification path was found; SHA-256 currently protects evidence files, not reports.

**Why it is a problem:** `report_id` is not stable for a session, report storage identity is distinct from the `report_id` presented in the payload, and finalized reports can be regenerated/changed. Different execution paths can also generate reports with different data sets.

**Proposed correction:** Separate stable report identity from immutable report revisions. Make finalization snapshot the complete QC state, attach an explicit revision ID and deterministic integrity digest, and reject changes to finalized revisions. Have all execution paths use the same report assembly.

**Change risk:** Existing consumers key reports by session ID and expect JSON/HTML payloads without revision metadata. Preserve those endpoints/fields while introducing stable identity and revision metadata.

**Tests required:** Identity remains stable across refresh; every revision is retrievable and immutable; finalized data cannot be altered; report integrity verification detects tampering; JSON/HTML represent the same revision; restart retrieval preserves revision history.

### P1-5 — Packaged Live mode defaults to file storage, which disables evidence endpoints

**Evidence:** `app/core/config.py:20-29`; `scripts/run_uhdp_live.sh`; `scripts/build_uhdp_live_iso.sh`; `app/api/evidence.py:24-35`.

**Existing behavior:** The Live launcher points report/session/data directories at the persistent USB partition but does not set `STORAGE_BACKEND`. The ISO build does not copy `.env`; `Settings` therefore defaults to `file` in the packaged environment unless an external environment value is supplied. The evidence API's `_require_sqlite()` returns HTTP 409 for every evidence operation when the backend is not SQLite.

**Why it is a problem:** Persistent JSON sessions/reports can use the USB data directory, but the packaged default cannot save or retrieve evidence through the evidence API. This leaves an explicit QC evidence requirement unavailable in the default Live configuration.

**Proposed correction:** Decide the Live persistence backend explicitly. Either set and validate SQLite in the Live launcher and verify its data path on the persistent partition, or implement evidence metadata/storage against the supported file backend. Keep the launcher fail-closed when persistent storage is absent.

**Change risk:** Switching Live from file to SQLite must preserve existing directory semantics and make sure database, evidence, and exported reports all reside on `UHDP_DATA`; do not move or overwrite technician data implicitly.

**Tests required:** Assert the packaged/default backend and resolved paths; verify evidence upload/list/download and checksum after application restart; verify no evidence or session data is written to the ephemeral root when the partition is absent. Physical reboot validation remains required.

### P2-1 — Persistence configuration varies by mode; local SQLite lifecycle lacks direct tests

**Evidence:** `app/core/config.py:20-29`; `app/persistence/repository_factory.py`; `app/persistence/local/database.py:16-66,963-993`; `app/persistence/local/migrations/0004_benchmark_session_links.sql`; `app/persistence/local/migrations/0004_outbox_boot_session.sql`; `app/evidence/storage.py`; `app/api/evidence.py`; `app/services/file_session_repository.py`; `app/workflows/reporting/file_report_repository.py`; `scripts/run_uhdp_linux.sh`; `scripts/run_uhdp_live.sh`.

**Existing behavior:** Development and the packaged Live image default to file-backed session/report repositories unless configuration overrides the setting. The regular Linux launcher defaults to SQLite and imports legacy JSON. SQLite has good foundations (transaction contexts, WAL, busy timeout, foreign keys, full synchronous mode, transactional migration application, and backups), but the file repositories write directly to their target JSON files. The two migrations named `0004_...` both apply because the migration key is the full filename; `schema_version` reduces the filename to its numeric prefix, so those two changes are not distinguishable in that integer.

**Why it is a problem:** Durability behavior and revision/crash semantics differ by launcher/configuration. No direct local SQLite migration/restart suite was found; existing reload coverage primarily tests `FileSessionRepository`.

**Proposed correction:** Decide and document the supported backend for each product mode; make evidence work through the supported repository boundary or explicitly reject unsupported modes before technicians rely on it. Keep the existing SQLite implementation unless tests reveal a concrete limitation. Give future migrations unique ordered versions and make backups/imports part of the migration procedure.

**Change risk:** Changing the backend default or SQLite path can strand existing sessions/reports or split data across stores. Preserve configured paths and make legacy JSON import explicit, idempotent, backed up, and observable.

**Tests required:** SQLite schema creation and upgrade from each supported prior version, rollback on migration failure, session/report/evidence restart round-trip, backup/restore, concurrent writes, and file-backend evidence behavior. Test Linux Live refusal when persistent storage is missing, but do not claim physical validation from mocks.

### P2-2 — Long-running diagnostics have a second job system and weak session coordination

**Evidence:** `app/services/diagnostic_job_service.py:54-128,187-280,628-767`; `app/runtime/managers/job_manager.py`; `app/runtime/context.py`; `app/main.py:29-46`.

**Existing behavior:** Runtime jobs use APScheduler; diagnostic jobs use a process-global two-worker `ThreadPoolExecutor` and per-job JSON files. Jobs queued/running at restart are marked failed rather than resumed. A completed job can mutate a session by calling `record_performance_result()` from the worker thread, while ordinary session requests also mutate the cached session dictionary. There is no shared session-operation lock across those paths.

**Why it is a problem:** Cancellation, progress, restart recovery, session persistence, and lifecycle shutdown are split across separate managers. Concurrent job/API updates can race while building/saving session reports.

**Proposed correction:** Keep specialized test loops but give them one lifecycle-managed job interface, explicit terminal/recovery states, and a serialized session update boundary. Do not introduce a distributed queue.

**Change risk:** Stress/battery durations, cancellation timing, and existing JSON job records are product behavior. Preserve current limits and migrate/recover prior job files without discarding history.

**Tests required:** Concurrent job and session update, job cancellation before/during execution, shutdown, restart recovery, progress persistence, and attachment of failed/cancelled as well as completed results.

### P2-3 — Discovery identity and platform support need a stable boundary

**Evidence:** `app/discovery/discovery_service.py:51-65`; `app/discovery/device_registry.py`; `app/discovery/models/device.py`; `app/hal/adapters/local_adapter.py`; `app/diagnostics/capability_catalog.py`; `tests/discovery/test_linux_inventory_providers.py`; `docs/LINUX_LIVE_USB.md`.

**Existing behavior:** Discovery is inventory-provider based and refresh replaces the registry. Provider IDs include category IDs and some index/device-derived IDs; there is no persistent component-matching layer. The capability catalog separately checks installed engines. Linux tests construct fake sysfs data or patch platform/tool calls; the Live USB documentation says image/launcher/hardware validation has not been run.

**Why it is a problem:** A refresh can change identity or lose ambiguity history, and tool availability is not the same as a supported/executable diagnostic. The generic HAL adapter does not provide a Windows/Linux adapter strategy. Current tests cannot establish actual hardware readiness.

**Proposed correction:** Keep existing providers and diagnostics; add a small explicit inventory identity/matching boundary and OS adapter capabilities only where needed. Keep discovery distinct from functional testing and represent unsupported/unavailable/precondition failures explicitly.

**Change risk:** Provider output shapes and category identifiers are consumed by UI and diagnostics. Do not replace working Linux probes or infer physical support from tool detection.

**Tests required:** Provider fixture regression tests on both platform paths, stable multi-component matching, missing/ambiguous hardware, and separate Linux/Windows acceptance runs on reference physical devices.

### P2-4 — Test coverage is present but does not prove all required contracts

**Evidence:** `tests/api/test_diagnostic_session_execution.py:39-46`; `tests/services/test_diagnostic_session_execution.py:73-78`; `tests/api/test_diagnostic_session_routes.py:95-103,138`; `tests/api/test_diagnostic_jobs.py`; `tests/services/test_file_session_repository.py:97-135`; `tests/discovery/test_linux_inventory_providers.py`.

**Existing behavior:** Some tests accept several unrelated outcomes (`workflow_status` in `success/failed/stopped`, broad report/test-result status sets). Job cancellation tests replace `_execute_test` with a fake. File repository tests validate serialization/reload, but do not restart the application. No focused local SQLite migration/restart or evidence checksum test was found. Linux provider tests are primarily fixture/mocked hardware checks.

**Why it is a problem:** Passing these tests would not establish expected outcome, durable SQLite behavior, real cancellation of a diagnostic process, report immutability, or physical hardware operation. One focused test already fails as described above.

**Proposed correction:** Add exact expected-state assertions and database/process-boundary integration tests as part of the corresponding implementation slices; keep tests that validate current manual/retest behavior.

**Change risk:** Avoid replacing environment-independent tests with fragile assumptions about whichever hardware is attached to a developer machine.

**Tests required:** Focused route/service tests, temporary-directory SQLite integration tests, process restart tests, deterministic fake-adapter tests, and separately recorded physical acceptance results.

### P3 — Architecture documentation predates important persistence/QC work

**Evidence:** `docs/UHDP_CODEBASE_MAP.md`; `docs/PROJECT_ARCHITECTURE_GIST.md` (repository baseline `f442a9c`); `docs/LINUX_LIVE_USB.md`.

**Existing behavior:** The codebase map describes JSON files as the persistence format and does not map the current local SQLite/outbox/evidence paths. The architecture guide documents earlier diagnostic paths and notes duplicate services, while the current working tree adds QC/manual/display workflows and SQLite functionality. Live documentation correctly labels its checks unvalidated.

**Why it is a problem:** Future changes can follow stale ownership descriptions or mistake planned behavior for verified behavior.

**Proposed correction:** Update only the affected architecture-map/guide sections after phases establish the canonical implementation; retain explicit unvalidated status for Linux Live and hardware claims.

**Change risk:** Documentation can overstate completion if updated before implementation and acceptance checks.

**Tests required:** No code tests for this documentation-only correction; verify claims against source and actual platform test evidence before recording them.

## C. Existing code worth retaining

- `app/hal/default_diagnostics.py`, the diagnostic registry/executor, and the existing diagnostic implementations. Reuse these rather than rewriting diagnostics as part of architecture work.
- `app/hal/diagnostic_evaluator.py` and its explicit inconclusive handling; extend rule coverage only when the catalog/acceptance policy requires it.
- The discovery providers and their Linux fixture tests. Preserve useful per-drive/provider detail while adding identity reconciliation.
- Manual-check definitions and the existing manual result/retest history, cosmetic inspection, and display attempt workflow in `DiagnosticSessionService`; strengthen lifecycle guards rather than replacing these features.
- SQLite persistence foundations: transaction context, WAL, `busy_timeout`, foreign keys, migrations, session/report revision snapshots, outbox, audit events, and backup integrity check.
- `EvidenceStorage` path validation, temporary-file write, SHA-256 capture and verification.
- Existing file session/report repositories and legacy import as compatibility/migration sources, while addressing atomicity where those repositories remain supported.
- Profiles, workflow templates, FastAPI route modules, frontend API wrappers, and Linux launchers. Refactor their orchestration boundaries without a ground-up rewrite.

## D. Proposed target architecture

Use the existing application layout and keep the API thin:

```text
Frontend/API adapters
        |
        v
QC/session services ---- QC decision policy
        |
        v
Canonical diagnostic service
  validate -> execute existing HAL diagnostic -> evaluate -> persist run/result
        |
        +--> discovery/platform adapters (inventory only)
        +--> job adapter (progress/cancel around the same execution service)
        +--> report/revision service
        +--> evidence service
        |
        v
SQLite local persistence + offline outbox
```

The service boundary should own identity translation and stable result contracts. Domain identity must distinguish physical asset, hardware component, QC session, diagnostic run, report/revision, and evidence. Keep `device_id` as a compatibility field where existing routes/clients require it. A finalized report should be an immutable snapshot with explicit revision/integrity metadata. Use the existing SQLite and file implementations as migration/compatibility choices; do not introduce microservices, a distributed queue, or a new ORM without a demonstrated need.

## E. File-level implementation roadmap

These are proposed minimum candidates, not authorization to edit them. Paths may be narrowed after each phase’s source/test review. Phase 1 is the only next phase for approval.

| Phase | Minimum candidate files |
|---|---|
| 0 — Audit | Create `docs/UHDP_BACKEND_AUDIT.md` (this document); no application changes. |
| 1 — Identity/domain models | Create `app/domain/assets.py` for asset/component records; update `app/discovery/models/device.py`, `app/services/diagnostic_session_service.py`, `app/persistence/local/database.py`, `app/persistence/session_serialization.py`; add a uniquely numbered `app/persistence/local/migrations/0006_asset_component_identity.sql`; update `app/api/sessions/diagnostic_routes.py` and `frontend/src/api/execution.ts` only for compatible identity fields. Add focused discovery, session-route, and local-database tests. |
| 2 — Canonical diagnostic engine | Update `app/runtime/services/diagnostic_service.py`, `app/hal/diagnostic_service.py` only as needed, `app/services/diagnostic_session_service.py`, `app/services/diagnostic_job_service.py`, the active diagnostic routes, `app/profiles/profile_service.py`, workflow diagnostic actions under `app/workflows/actions/diagnostics/`, and their unit/integration tests. |
| 3 — Diagnostic catalog | Update `app/diagnostics/capability_catalog.py`, `app/hal/default_diagnostics.py`, `app/profiles/`, `profiles/*.json`, `app/api/capabilities.py`, and catalog/profile tests. |
| 4 — Discovery/adapters | Update `app/discovery/discovery_service.py`, `app/discovery/device_registry.py`, relevant `app/discovery/providers/`, `app/hal/adapters/`, `app/hal/diagnostics/platform_probes.py`, and provider/adapter tests. Add a Windows adapter only for verified platform needs. |
| 5 — QC workflow | Update `app/services/diagnostic_session_service.py`, `app/api/sessions/diagnostic_routes.py`, `app/diagnostics/manual_checks.py`, and matching frontend API/session workflow files under `frontend/src/api/` and `frontend/src/session/`; extend route/service tests. |
| 6 — QC decision/approval | Add a focused decision-policy module under `app/diagnostics/` or the existing service boundary; update technician/session request schemas, persistence serialization/schema only if required, report assembly, and decision/approval tests. |
| 7 — Persistence | Update `app/persistence/local/database.py`, `app/persistence/local/migrations/`, `app/persistence/repository_factory.py`, local repositories and serialization, `app/persistence/local/import_legacy.py`, launcher defaults only after backend selection; add SQLite migration/restart/backup tests. |
| 8 — Evidence | Update `app/evidence/storage.py`, `app/api/evidence.py`, persistence evidence records, and `frontend/src/api/` evidence callers; add file/metadata rollback, checksum, size-limit, and session/run-link tests. |
| 9 — Reports | Update `app/workflows/reporting/report_builder.py`, `app/workflows/reporting/diagnostic_report.py`, `app/persistence/local/repositories.py`, `app/workflows/reporting/file_report_repository.py`, `app/reports/` only where active callers require it, and `app/api/reports.py`/`reports_export.py`; add stable-ID/revision/finalization tests. |
| 10 — Jobs/resources | Update `app/services/diagnostic_job_service.py`, `app/api/diagnostic_jobs.py`, runtime lifecycle wiring in `app/main.py`/`app/runtime/context.py`, and job tests; retain bounded local execution. |
| 11 — API contract | Update only active routers in `app/api/`, matching wrappers in `frontend/src/api/execution.ts` and `frontend/src/api/reports.ts`, and API contract tests. Retire or leave unmounted legacy route modules deliberately; do not silently add them to router composition. |
| 12 — Configuration/logging | Update `app/core/config.py`, `app/core/logging.py`, launcher scripts, `.env.example`, and focused configuration/startup tests. |
| 13 — Cloud readiness | Update `app/sync/worker.py`, SQLite outbox/repository methods and migrations, sync routes, and sync tests. Keep offline local creation independent of cloud availability. |
| 14 — Acceptance testing | Extend tests under `tests/api`, `tests/integration`, `tests/persistence`, `tests/discovery`, and `tests/hal`; separately execute and record Windows/Linux physical-hardware checks. |
| 15 — Documentation | Update `docs/UHDP_CODEBASE_MAP.md`, `docs/PROJECT_ARCHITECTURE_GIST.md`, and add/update only the required workflow/API/data-model/implementation documents once behavior is implemented. Preserve `docs/LINUX_LIVE_USB.md` validation caveats until checked on hardware. |

## F. Database migration risks

- Sessions/reports currently exist as JSON files in file mode and as SQLite JSON payloads plus normalized rows/revisions in SQLite mode. Migration must preserve the session/report identifiers, result/evidence references, and any report history; do not infer `asset_id` from an ambiguous `device_id`.
- The regular Linux launcher runs `app.persistence.local.import_legacy` when SQLite is selected. Verify its idempotence, failure reporting, backup/rollback behavior, and collision handling before changing its inputs or default backend.
- `schema_migrations` keys full filenames, but the exposed integer schema version parses only the numeric prefix. Assign future migrations unique ordered prefixes rather than another `0004_*`.
- SQLite session, report, run, and evidence tables contain foreign keys. Backfills must create parent rows before dependent records and run integrity checks after migration.
- A session update and report save are separate repository operations, not one transaction. A failure between them can leave the latest session and report out of sync.
- Back up the configured database and relevant evidence/report directories before production migration; test restore on a copied database before deployment.

## G. API compatibility risks

- The frontend’s active QC clients use `/diagnostic-sessions/`, session detail/intake/manual/display/completion/finalization/reopen routes, `/reports/`, and `/reports/{session_id}/json|html`. Preserve these paths and existing `device_id` fields while adding canonical identifiers.
- The direct diagnostic route returns raw `status`; session routes return `status`, `raw_status`, and `execution_status`; profile/job responses use their own response shapes. Changing to a new result contract must preserve these legacy fields during a migration window.
- `/complete` currently returns `checks_complete`, while a test asserts `completed`. Decide the intended contract together with the frontend state machine.
- `final_disposition` values are an API `Literal`; `test_station_profile_retest_and_qa_disposition_persist_in_report` sends `"CONDITIONAL PASS"` and expects HTTP 200, but that value is not in the request model's allowed enum and is rejected with HTTP 422. Align the test/API/UI enum only after agreeing the public dispositions.
- Report lookup is keyed by session ID even though report payloads have a separate, regenerated `report_id`. Keep session-based lookup while introducing stable report/revision identifiers.
- The duplicate legacy route modules are not mounted; changing router composition can unexpectedly expose them or create path conflicts. Check OpenAPI/router registration in the API-contract phase.

## H. Test and hardware validation plan

1. **Unit:** canonical execution state machine and evaluator outcomes; stable asset/component matching; report revision serialization; policy-based QC completion.
2. **API integration:** all active execution entry points return consistent statuses/IDs; preserve frontend request/response shapes; reject invalid workflow selections; enforce finalized-session edit restrictions.
3. **Persistence:** SQLite migrations from supported prior versions; save/reopen across a fresh process; evidence metadata/file/checksum round-trip; report/session consistency; backup/restore; concurrent session/job writes. Exercise file mode separately if it remains supported.
4. **Jobs:** progress, cancellation before/during execution, worker shutdown, restart recovery, and attaching all terminal outcomes to the intended session.
5. **Frontend:** run the existing production build when API changes reach a frontend caller; no dedicated frontend lint/test script is currently configured.
6. **Physical acceptance:** on documented reference Linux Live and Windows machines, record model, OS/kernel, BIOS/UEFI, drivers/tool versions, and exact results for CPU, RAM, storage, battery, GPU, display, keyboard, touchpad, webcam, audio, Wi-Fi, Bluetooth, and USB. Include offline/restart persistence checks. Fixture tests and this audit do not count as physical hardware validation.

## I. Dependency recommendation

**No dependency changes are recommended for Phase 0 or the initial identity/canonical-pipeline slices.** `sqlite3` is in the standard library; `pydantic-settings` and `psutil` are already pinned. The current migration code is small enough to continue with after assigning unique versions and adding direct tests. Consider SQLAlchemy/Alembic only if the schema/repository redesign demonstrates that hand-written migrations are a concrete maintenance problem. Do not add `structlog`, `httpx`, or other proposed packages until a specific requirement justifies them; the sync worker currently uses the standard library.

## Phase 1 identity scope — initial implementation

Identity modeling was initially implemented without unifying diagnostic execution or changing report assembly. `device_id` remains a compatibility/discovery reference. The initial implementation and its verification findings are historical context below; Phase 1 is not approved to gate Phase 2.

## Phase 1 identity verification gate — 2026-11-04

This verification inspected the current Phase 1 worktree, including the pre-existing uncommitted changes. Source was read directly because the Codebase Memory snapshot predates those edits; migration `0006` was also marked partially parsed by the index. No production database, frontend page, cloud schema, or migration was changed.

**Asset identity:** A session uses an explicitly supplied `asset_id`; otherwise it reuses the asset from a valid `retest_of_session_id` pointing to an identified session, or generates a UUID. An explicit `asset_id` can override the prior session's asset even on a retest; the service does not check that override against the retested asset. Asset tags and discovered serials enrich metadata but do not match an existing asset. Thus a physical device can retain an ID across linked sessions/retests, but the application does not independently recognize that device across unrelated new sessions; uncertain identity defaults to a new asset rather than a provisional match. `device_id` is not used as `asset_id`. Legacy sessions/runs are left unlinked; an asset is created only when the legacy session next needs one, without retroactively linking its historical runs.

**Component identity:** The implementation permits multiple components in a category and derives asset-scoped IDs from a category plus a serial/WWN/PCI address, storage path, provider ID, or memory serial/slot/reported index. Discovery deduplicates identical keys, and SQLite enforces uniqueness per asset/key. Distinct keys can represent replacements. However, weak provider-ID and reported-index fallbacks are persisted as ordinary identities, not marked provisional; changed provider IDs can fragment identity, while reused IDs/indexes can merge a replacement. No universal fingerprint is present.

**Diagnostic runs and evidence:** Normal diagnostic requests receive a UUID `diagnostic_id`; `DiagnosticResult.run_id` is exactly an alias of that ID, not an independent ID. New requests/retests therefore normally create new IDs, and new IDs append history. Persistence upserts on `run_id`, however, so resaving the same ID overwrites its prior result; the alias has no independent uniqueness protection. Application checks and SQLite foreign keys/triggers reject cross-session run assignment and reject evidence whose run belongs to a different session. Composite identity foreign keys constrain canonical runs/components to their session asset. Evidence has no `asset_id` column, so cross-asset ownership is only inferable through a canonical run identity; legacy runs without that identity cannot establish an evidence asset relationship.

**Reports:** The session retains a stable `report_id`; each rebuild receives a distinct `revision_id`. SQLite stores report revision snapshots and the audit test confirmed two revisions remain in the database. The report API/repository exposes the current/latest report, not a way to retrieve a selected historical revision. Finalization sets session status but does not freeze report content: later writable session paths can save another revision and replace the current report. Cloud report writes likewise upsert the current payload rather than retaining revision history.

**SQLite migration 0006:** Temporary databases were used for fresh initialization, a pre-0006 database containing sessions, diagnostic runs/results, reports/revisions, and evidence, and a second initialization through the normal migration runner. Existing rows remained intact; fresh initialization created the identity tables; repeat initialization skipped the already-recorded filename. The SQL file itself is not idempotent if run directly a second time (`CREATE TABLE` lacks `IF NOT EXISTS`); safety depends on `schema_migrations`. There is no down migration. Recovery expectation is to back up the database and restore that backup if migration fails; production migration and restore were not attempted. The existing migration guidance in section F requires a database/evidence backup and a tested copied-database restore.

**Cloud compatibility:** The active Supabase repositories store session/report payloads in the generic `uhdp_records` JSONB payload, so the added identity keys do not require new columns there. The separate normalized cloud schema does not itself define the new asset/component/run identity structures, and the active repositories do not write those structures into it. No live Supabase operation was tested; cloud revision history/identity synchronization is not verified.

**Tests and outcome:** `tests/persistence/test_identity_foundation.py` — **11 passed** (including temporary fresh, representative, and repeat-migration checks). The session/report API selection (`test_diagnostic_session_routes.py`, `test_diagnostic_session_execution.py`, and three report API/export files) — **26 passed, 2 failed**: `/complete` returned `checks_complete` instead of expected `completed`; technician API returned 422 for `CONDITIONAL PASS`. The full backend suite — **466 passed, 2 failed, 19 warnings**; the same two failures occurred. These are the two documented failures and were not changed. `git diff --check` passed before this audit section was added; the final check was run after the report update.

**Not verified:** Physical-device continuity/replacement matching, live cloud schema behavior, production migration, and actual backup restoration. The tests verify local SQLite/source contracts only.

**Gate decision:** **Phase 1 is not ready to gate Phase 2.** Asset matching across independently created sessions is absent, uncertain component identities are not provisional, duplicate run IDs overwrite existing records, and finalized reports are mutable with no historical-revision retrieval path. This is a verification finding only; no Phase 2 work or identity redesign was started.

## Phase 1 corrective work — 2026-11-04

This update supersedes the initial implementation findings above for the behaviors corrected here. It is limited to asset identity, diagnostic run identity, component identity, and report revision integrity. No Phase 2 work, canonical diagnostic engine, frontend page/navigation change, cloud synchronization, dependency, Supabase schema change, or production migration was introduced.

### Corrected behavior

- **Assets:** A new session is unresolved by default (`asset_id` remains null). A client can link an existing asset by supplying its `asset_id`, which must already exist, or explicitly create an asset with `create_asset: true`. `asset_id` and `create_asset` cannot be combined. Retests inherit the source session's asset ID; an explicitly matching ID is accepted and a conflicting ID is rejected. A retest of a legacy session with no asset remains unresolved; it cannot assign a new or supplied asset. No hardware-identifier matching or automatic merge is performed. Legacy sessions are not assigned invented assets.
- **Diagnostic runs:** `diagnostic_id` identifies the diagnostic definition/type; each `DiagnosticExecutor.execute()` invocation assigns a fresh `run_id`, even when the same request object is reused. Retests execute with new run IDs. Persistence keys diagnostic runs/results by `run_id`, rejects changed content under an existing run ID, and skips legacy results without a run ID rather than using `diagnostic_id` as a key. Legacy diagnostic payloads remain readable with `run_id: null` and their original `diagnostic_id` intact; historical database rows are not rewritten.
- **Components:** `HardwareComponent.provisional` is true for provider IDs, PCI addresses, paths, slots, reported indexes, or missing provider IDs; it is false only when a unique serial number or world-wide name is available. Duplicate serials fall back to provisional provider/slot/index identities. Components remain asset-scoped; modules/devices with distinct reliable identifiers retain distinct IDs, rediscovery with the same deterministic key reuses the ID, and a changed confirmed serial yields a distinct component. This is deliberately not a universal fingerprint; provisional IDs can change when provider IDs or reported ordering change.
- **Reports:** The per-session `report_id` remains stable while each refresh creates a new `revision_id`. The existing `/reports/{session_id}/revisions` route returns the full local report history. File and SQLite repositories reject changed content under an existing revision ID and require an attributed superseding revision after finalization. Session edit paths now reject finalized sessions before mutating their in-memory state; explicit reopen-for-retest creates a new revision linked to the finalized revision. Existing JSON/HTML report representations remain available.

### Persistence, validation, and limitations

- **Migrations:** No migration was changed or added for this correction. The existing additive `0006_asset_component_identity.sql` and `0007_report_revision_integrity.sql` were inspected and exercised through the normal SQLite migration runner using temporary databases. Existing session, diagnostic run/result, evidence, report, and report-revision rows remained readable. No production database was migrated and no historical record was rewritten.
- **Focused tests:** The identity foundation, session/diagnostic persistence, report API, and report revision selection completed with **59 passed, 2 failed**. The two failures are the already documented unrelated `/complete` status (`checks_complete` versus expected `completed`) and technician disposition validation (`CONDITIONAL PASS` returns HTTP 422); neither was changed.
- **Full backend suite:** `pytest -q --tb=short` completed with **475 passed, 5 failed, 19 warnings**. Besides the two failures above, three untouched workflow API tests failed because their empty-action workflow payloads are rejected (`test_list_workflows`, `test_get_workflow`, and `test_execute_workflow`). These are outside this corrective scope and were not changed.
- **Cloud:** No live Supabase/cloud operation was run. Cloud behavior, identity persistence, and report revision history are **not tested or claimed ready**; inspecting JSON payload shape alone is not cloud validation. The active Supabase report repository does not currently implement historical revision/finalization operations, so revision API behavior is verified only for local file/SQLite repositories.
- **Remaining limitations:** Asset selection is explicit; there is no automatic asset matching. Provisional component identities are intentionally weak and can fragment when discovery IDs/order changes. Legacy diagnostic records without a run ID remain readable but cannot be linked as canonical runs. Production migration/restore, physical hardware behavior, and live cloud behavior remain unverified.

**Gate decision:** Phase 1 remains **not approved to gate Phase 2**. Stop here pending approval; no Phase 2 implementation was started.
