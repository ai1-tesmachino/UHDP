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

## Final Phase 1 readiness, dependency, and Supabase review — 2026-11-04

This section is the final read-only verification supplement to the historical Phase 0 and corrective-work findings above. The checked-out commit was `8767f9c753eddcd40ef0be71f3450836560cbb59` (`main`). The worktree was clean before this documentation update. No application code, dependency manifest/lockfile, database schema, or production data was changed. Tests used temporary data directories and migration-test databases only.

### Readiness outcome

| Area | Verified behavior | Remaining limitation |
|---|---|---|
| Asset identity | API distinguishes unresolved (`asset_id: null`), explicit existing-asset link, explicit asset creation, and retest inheritance. A conflicting retest asset is rejected. Legacy unresolved identity remains unresolved. | All current technician UI session-creation callers omit both `asset_id` and `create_asset`; the normal workflow therefore creates unresolved sessions without presenting a resolution step. |
| Diagnostic run identity | Executions and retests get distinct `run_id` values; diagnostic definitions keep their `diagnostic_id`; local persistence rejects changed content when a run ID is reused. | Live cloud persistence and cloud ownership behavior were not tested. |
| Component identity | A unique serial number or WWN is confirmed; provider ID, PCI/path/slot/index, missing, or duplicate serial identities are provisional. Distinct slots/indices allow multiple modules/devices; rediscovery reuses matching deterministic identities. | Provisional identities can fragment when provider IDs/order change, and a reused weak ID can obscure a replacement. No universal fingerprint is attempted. |
| Reports | Local file/SQLite report identity is stable per session, revision IDs are distinct, revision history is available at `/reports/{session_id}/revisions`, and finalized revision payloads are immutable. | The local reopen API records an actor label but does not authenticate or authorize that actor. The Supabase report adapter does not implement revision history/finalization. |
| Migrations | SQLite migrations 0006/0007 passed fresh, representative-data, repeat-initialization, ownership-constraint, and finalization tests using temporary databases. | No production migration/restore, cloud migration, Linux deployment, or live Supabase operation was performed. |

**Gate decision:** Phase 1 remains **not approved to gate Phase 2**. In particular, ordinary technician-created sessions stay unresolved and the UI has no explicit asset-resolution flow. This review does not add automatic matching or change the frontend.

### Session creation callers and unresolved identity

The active frontend request wrapper is `frontend/src/api/execution.ts:createDiagnosticSession`. Its intake type does not expose `asset_id` or `create_asset`, and the `DiagnosticSession` frontend type does not expose the returned `asset_id`.

| Caller | Request made | Identity behavior |
|---|---|---|
| `frontend/src/pages/DeviceDiscovery.tsx:137` | `createDiagnosticSession(systemDevice.device_id, intake)`; intake has asset tag/technician/station/customer/workflow fields only. | Omits both identity fields. `device_id` is not converted into an asset ID; the created session remains unresolved. |
| `frontend/src/session/SessionContext.tsx:81,124` | `createDiagnosticSession(undefined, undefined, sessionId)` for starting/resuming a pending session. | Omits both fields and creates/recovers an unresolved session. |
| `frontend/src/pages/QcInspection.tsx:196` | `createDiagnosticSession(undefined, {..., workflow_type: "standalone_manual_diagnostic"})`. | Omits both fields; standalone manual sessions remain unresolved. |
| Backend `POST /diagnostic-sessions/` (`app/api/sessions/diagnostic_routes.py`) | Accepts `asset_id` and `create_asset`; `DiagnosticSessionService.create_session()` validates them. | API tests verify explicit existing-asset linking, explicit creation, retest inheritance, matching retest IDs, conflict rejection, and unresolved legacy retests. No current frontend caller supplies these fields. |
| Backend `POST /sessions/` (`app/api/sessions/routes.py`) | Creates a separate generic session via `SessionService`. | No asset resolution fields; no active frontend caller was found. It is not the QC session-creation contract. |

No frontend caller was found supplying `retest_of_session_id`; the field exists in the request type, but there is no UI retest-creation path in the inspected callers. A user can create/link assets through the backend contract, but there is no frontend asset picker/creation choice and no UI indication that a session remains unresolved. Thus unresolved identity is represented correctly in backend data, but normal technician QC does not resolve it or tell the technician it is unresolved. A future change needs an explicit workflow decision; automatic matching by weak hardware identifiers is not recommended.

### Identity and report contract confirmation

- `DiagnosticSessionService.create_session()` reuses an identified source session's asset on retest, accepts an explicit matching ID, rejects a conflicting ID, and prevents a legacy unresolved retest from acquiring a new ID. New sessions are unresolved unless a caller links an existing asset or sets `create_asset: true`. No historical asset association is inferred from `device_id`, serial text, or other weak identity.
- `DiagnosticExecutor.execute()` assigns a new UUID `run_id`; `diagnostic_id` remains the diagnostic definition/type. SQLite persists executions by `run_id`; reusing an existing ID with different content fails rather than overwriting. Historical rows without canonical IDs remain readable and are not rewritten.
- `HardwareComponent.create()` marks only unique `serial_number` and `world_wide_name` bases as confirmed. Other bases are provisional. Duplicate serials fall back to weak identities; memory slots and reported indices keep repeated RAM modules distinct. Storage/provider/path identities are provisional. Matching a stable key permits rediscovery; a changed confirmed serial yields a different component. Weak-ID replacement cannot always be distinguished from rediscovery.
- Local report refreshes retain the session's `report_id` and create distinct `revision_id` values. The report API returns the local revision list. File/SQLite repositories reject altered content under an existing revision ID and require a superseding revision with a reason and actor label after finalization. SQLite migration 0007 prevents revision payload updates/deletes and repeat finalization.
- Finalization attribution is not authorization: `/reopen` has no authenticated actor/role check, and the service derives an actor label from technician fields or falls back to `"operator"`. The immutable revision/audit behavior is verified locally; privilege enforcement is not implemented or claimed.
- The legacy JSON and HTML export paths remain present. Cloud/Supabase report writes are not equivalent to local revision behavior.

### Migration 0006/0007 safety and test evidence

`0006_asset_component_identity.sql` adds the asset/component/session/run identity tables, uniqueness and foreign-key relationships, and triggers enforcing run/session and evidence/run ownership plus immutable session/asset links. `0007_report_revision_integrity.sql` adds finalization/supersession metadata and triggers that make revision payloads immutable, make finalization one-way, and prevent revision deletion. Neither migration was edited in this audit.

`SQLiteDatabase._migrate()` applies each pending SQL file inside `BEGIN IMMEDIATE`, records the filename in `schema_migrations` in the same transaction, and skips a filename already recorded. A migration failure rolls back the transaction through the connection context; there is no down migration. The documented recovery expectation is to back up the database and restore that backup if an upgrade fails; a production backup/restore was not attempted.

The passing identity-foundation tests exercise fresh database initialization (`test_asset_identity_migration_applies_to_fresh_database_and_repeats_safely`), a representative database containing historical session/run/result/evidence/report/revision rows (`test_additive_migration_preserves_preexisting_session_and_run_rows`), invalid ownership relationships (`test_session_and_run_asset_ownership_are_enforced`), and finalized-revision immutability/supersession (`test_finalized_report_revision_is_immutable_and_requires_explicit_supersession`). They verify that legacy rows remain readable and that no asset/run identity rows are fabricated for legacy records. The API history test `test_report_revision_history_route_exposes_all_revisions` also passes. These checks use temporary databases only. `cloud/migrations/0001_cloud_schema.sql` and `0002_conflict_station.sql` are a separate PostgreSQL cloud schema and were not applied; no Supabase schema or production database was changed.

### Three workflow API test failures

The three empty-action failures were compared at baseline `70e96983473669ceea092371a6a507549da9c0ab` and current `HEAD` in separate temporary data directories with the same Python environment and explicit file-backend settings. Each run of `tests/api/test_workflows.py` produced **3 failed, 4 passed**; the same failures reproduce at baseline, so they are **not regressions**. An earlier comparison without matched working-directory/data settings was not reliable; the controlled result here supersedes it.

| Test | Failure reason at baseline and current | Normal technician QC impact |
|---|---|---|
| `tests/api/test_workflows.py::test_list_workflows` | The test POSTs `actions: []`; the API rejects it with HTTP 400 (`Workflow must contain at least one action.`), so `list_test` is absent from the returned list. | No direct frontend `/workflows` caller was found. |
| `tests/api/test_workflows.py::test_get_workflow` | The empty-action POST is rejected with HTTP 400; the subsequent GET returns 404. | No direct frontend `/workflows` caller was found. |
| `tests/api/test_workflows.py::test_execute_workflow` | Both empty-action creation requests are rejected with HTTP 400; execution then returns 404. | No direct frontend `/workflows` caller was found. The normal technician UI uses the diagnostic-session API; no impact on that flow was observed. |

These are test/API contract failures for invalid empty workflows, not evidence that valid action-bearing workflow execution fails. They were not changed. The two separately documented failures also remain: `/complete` returns `checks_complete` rather than the test's `completed`, and `CONDITIONAL PASS` is rejected by technician-record validation.

### Dependency and package inventory

The dependency files found in the repository are `requirements.txt`, `cloud/requirements.txt`, `frontend/package.json`, and `frontend/package-lock.json`. There is no `pyproject.toml`, Python lockfile, separate Python development/test requirements file, or separate frontend test manifest. The cloud requirements file pins its five direct dependencies but does not lock its transitive graph. The frontend lockfile resolves the frontend graph; the Python root requirements file pins direct and transitive packages in one flat list.

#### Python packages

The current local environment is Python **3.14.7**. `pip check` reported **No broken requirements found**. Package versions below are the root requirements pins/current installed values; packages with a Linux marker are not expected in this Windows environment.

| Direct package | Declared pin | Installed in current app venv | Observed use | Classification |
|---|---:|---:|---|---|
| FastAPI | 0.141.1 | 0.141.1 | Backend and separate cloud HTTP APIs; request routing and dependency injection. | Required |
| Pydantic | 2.13.5 | 2.13.5 | API request models and runtime/domain validation. | Required |
| pydantic-settings | 2.15.0 | 2.15.0 | Environment and `.env` configuration in `app/core/config.py`. | Required |
| Uvicorn | 0.53.0 | 0.53.0 | Backend/cloud ASGI process; Linux launchers invoke it. | Required |
| APScheduler | 3.11.3 | 3.11.3 | Runtime `JobManager` scheduling. | Required for scheduled runtime jobs |
| psutil | 7.2.2 | 7.2.2 | CPU, memory, storage, network, battery, and monitoring providers/diagnostics. | Required |
| pyudev | 0.24.3 | 0.24.3 | Dynamically imported Linux device probing; discovery has a fallback. | Optional platform integration |
| pyusb | 1.3.1 | 1.3.1 | Capability catalog checks for the `usb` module; no operational `usb.core`/`usb.util` use was found. | Optional/unverified; candidate for review |
| evdev | 1.9.2, Linux-only marker | Not installed (Windows marker) | Capability catalog checks module availability; no operational import was found. | Optional/unverified |
| PyYAML | 6.0.3 | Not installed | No use found in application, cloud, scripts, tests, or profiles. | Unused in the verified source scope |
| python-dotenv | 1.2.3 | 1.2.3 | `pydantic-settings` `.env` support and Linux launcher's `dotenv_values()` helper. | Required for current configuration path |
| pytest | 9.1.1 | 9.1.1 | Backend tests; included in the root requirements installed by the Live image hook. | Test-only, currently bundled with runtime pins |

The root manifest also pins these transitive/runtime-support packages: `annotated-doc==0.0.5`, `annotated-types==0.8.0`, `anyio==4.15.1`, `click==8.5.0`, `colorama==0.4.6`, `h11==0.16.0`, `httptools==0.8.0`, `idna==3.20`, `iniconfig==2.3.0`, `packaging==26.3`, `pluggy==1.6.0`, `pydantic_core==2.46.5`, `Pygments==2.21.0`, `starlette==1.7.0`, `typing-inspection==0.4.4`, `typing_extensions==4.16.0`, `tzdata==2026.4`, `tzlocal==5.4.4`, `watchfiles==1.3.0`, and `websockets==17.1`. They support FastAPI/Pydantic/Uvicorn/APScheduler or pytest; they are not separately imported as application features. The current environment also has `pytest-asyncio` 1.4.0 and Starlette's `httpx2`/`httpcore2` test-client stack, but these are not separately declared as direct test dependencies. Tests pass in the current environment; a clean Python installation from the tracked requirements is not a reproducible test environment because no dedicated test manifest/lock exists.

The independent `cloud/requirements.txt` pins these direct dependencies:

| Cloud package | Declared pin | Installed in current app venv | Observed use | Classification |
|---|---:|---:|---|---|
| FastAPI | 0.141.1 | 0.141.1 | Cloud API routes and authentication dependencies. | Required for cloud service |
| Pydantic | 2.13.5 | 2.13.5 | Cloud request models and validation. | Required for cloud service |
| Uvicorn | 0.53.0 | 0.53.0 | Cloud ASGI process in `cloud/Dockerfile`. | Required for cloud service |
| `psycopg[binary]` | 3.2.10 | Not installed | PostgreSQL driver used by the cloud database layer. | Required for cloud service |
| boto3 | 1.41.2 | Not installed | Optional S3-compatible object/evidence storage client. | Optional integration |

The cloud image is based on `python:3.12-slim`; the compose stack uses `postgres:16`. The cloud code is not copied into the Live image. Cloud transitive installed versions were not available in the local environment for verification.

#### Frontend packages

`npm --prefix frontend ls --depth=0` resolved all 22 direct dependencies without invalid peers. `frontend/package-lock.json` contains 274 unique resolved package entries; `npm ls --all` traversed the installed graph with no invalid nodes. The current runtime is Node **24.21.0** / npm **11.19.0**.

| Direct dependency | Declared range | Installed | Observed use | Classification |
|---|---:|---:|---|---|
| `react`, `react-dom` | `^19.1.1` / `^19.1.1` | 19.3.0 / 19.3.0 | Application/component runtime and browser rendering. | Required |
| `react-router-dom` | `^7.8.2` | 7.18.4 | Route and page navigation. | Required |
| `axios` | `^1.11.0` | 1.20.0 | API client and HTTP requests. | Required |
| `@hookform/resolvers` | `^7.0.2` | 7.0.2 | `zodResolver` in technician assessment form. | Required |
| `react-hook-form`, `zod` | `^7.91.0` / `^4.6.7` | 7.91.0 / 4.6.7 | Form state and validation. | Required |
| `radix-ui` | `^1.8.1` | 1.8.1 | Existing accessible UI primitives. | Required |
| `class-variance-authority`, `clsx`, `tailwind-merge` | `^0.7.1` / `^2.1.1` / `^3.7.0` | 0.7.1 / 2.1.1 / 3.7.0 | Component variants and class-name composition/merging. | Required; complementary roles |
| `lucide-react` | `^1.67.0` | 1.67.0 | UI icons. | Required |
| `sonner` | `^2.0.8` | 2.0.8 | Toast notifications. | Required |
| `tailwindcss`, `@tailwindcss/vite`, `tw-animate-css` | `^4.3.4` / `^4.3.4` / `^1.4.0` | 4.3.4 / 4.3.4 / 1.4.0 | Styling, Vite integration, and CSS animations. | Required |
| `vite`, `@vitejs/plugin-react` | `^7.1.3` / `^5.0.2` | 7.3.7 / 5.2.0 | Development/production bundling and React transform. | Build dependencies |
| `typescript` | `^5.9.2` | 5.9.3 | Frontend type checking/transpilation. | Build dependency |
| `@types/react`, `@types/react-dom`, `@types/node` | `^19.1.10` / `^19.1.7` / `^22.20.5` | 19.3.0 / 19.3.0 / 22.20.5 | Type declarations for React and the Node-based Vite configuration. | Development/build dependencies |

There are no frontend testing or lint scripts/dependencies configured. No Supabase JavaScript SDK is present.

#### Python / npm release and security snapshot

Read-only PyPI release metadata and package-manager outdated checks were consulted on the audit date. These are latest-index observations, not upgrade recommendations:

| Python package | Pinned | Latest observed |
|---|---:|---:|
| FastAPI | 0.141.1 | 0.162.0 |
| Pydantic | 2.13.5 | 2.14.2 |
| pydantic-settings | 2.15.0 | 2.16.2 |
| Uvicorn | 0.53.0 | 0.54.0 |
| APScheduler | 3.11.3 | 3.11.3 |
| psutil | 7.2.2 | 7.2.2 |
| pyudev | 0.24.3 | 0.24.5 |
| PyUSB | 1.3.1 | 1.3.1 |
| PyYAML | 6.0.3 | 6.0.3 |
| python-dotenv | 1.2.3 | 1.2.4 |
| boto3 (cloud) | 1.41.2 | 1.43.123 |
| psycopg (cloud) | 3.2.10 | 3.3.8 |

The installed FastAPI/Pydantic/Starlette set passes `pip check`; the active API and full backend suite run on Python 3.14.7. PyPI metadata for current FastAPI, Pydantic, pydantic-settings, Uvicorn, and cloud package releases permits Python 3.10 or later (pydantic-settings latest requires 3.11 or later). This does not substitute for Linux/Debian 13 build or hardware validation. No evidence of a current FastAPI/Pydantic major-version conflict was found.

`npm outdated` identified in-range latest versions of Axios 1.21.0, Lucide 1.68.0, React/React DOM 19.3.1, and React Router 7.18.5. Latest versions outside the declared major ranges include Vite 8.3.5, TypeScript 7.0.2, `@vitejs/plugin-react` 6.2.1, and `@types/node` 26.6.6; the project is deliberately on Vite 7, TypeScript 5, plugin 5, and Node types 22. No newer latest version was reported for the other direct frontend dependencies. Those major upgrades require compatibility testing and are not recommended as automatic updates. The current Vite 7 production build succeeds on Node 24.

PyPI metadata showed 2026 releases for the main API/validation/server packages, APScheduler, psutil, pyudev, boto3, and psycopg. The latest PyUSB release observed was 1.3.1 (2025-01-08); PyYAML 6.0.3 was published 2025-09-29 and has no current application use. The primary stack is actively releasing; PyUSB is optional and its slower release cadence is not a blocker for the current usage. The `pip list --outdated` scan also reported these installed update pairs: `anyio` 4.15.1 -> 4.16.0, `httpcore2` 2.13.1 -> 2.16.0, `httptools` 0.8.0 -> 0.9.0, `httpx2` 2.13.1 -> 2.16.0, `iniconfig` 2.3.0 -> 2.3.1, `pip` 26.2.1 -> 26.3, `pluggy` 1.6.0 -> 1.7.0, `pydantic_core` 2.46.5 -> 2.50.2, `pytest` 9.1.1 -> 9.2.0, `pytest-asyncio` 1.4.0 -> 1.4.1.post1, `truststore` 0.10.4 -> 0.10.5, `tzdata` 2026.4 -> 2026.6, `tzlocal` 5.4.4 -> 5.4.5, `uv` 0.12.22 -> 0.13.7, and `websockets` 17.1 -> 17.4. These include transitive/test/environment packages, not just application direct dependencies; the full set was not upgraded.

`npm audit` reported **0 vulnerabilities** across the locked frontend tree. Read-only OSV queries of all **37 exact manifest pins** in the root/cloud Python requirements returned **no advisories** (the same packages pinned in both manifests are counted twice). `pip-audit` is not installed and was not added. The OSV result is limited to those pinned versions; the cloud transitive graph is not locked, Debian package advisories were not audited, and this is not a claim that the overall supply chain is vulnerability-free. Sources were the official PyPI and npm package registries, npm audit, and the OSV query API.

#### Linux system packages and external utilities

These are OS packages/executables, not Python/npm dependencies. `scripts/install_linux.sh` installs the following Debian packages (plus a Chromium/Firefox browser choice): `acpi`, `alsa-utils`, `build-essential`, `ca-certificates`, `bluez`, `dmidecode`, `dnsutils`, `edid-decode`, `ethtool`, `evtest`, `fio`, `fwupd`, `glmark2`, `intel-gpu-tools`, `iproute2`, `iputils-ping`, `iperf3`, `iw`, `lshw`, `libasound2-dev`, `libevdev-dev`, `libudev-dev`, `libusb-1.0-0`, `lm-sensors`, `libinput-tools`, `memtester`, `mesa-utils`, `nodejs`, `nvtop`, `npm`, `nvme-cli`, `pipewire`, `pciutils`, `pkg-config`, `python3`, `python3-dev`, `python3-evdev`, `python3-pip`, `python3-pyudev`, `python3-usb`, `python3-venv`, `rfkill`, `smartmontools`, `sysstat`, `stress-ng`, `tpm2-tools`, `usbutils`, `util-linux`, `upower`, `v4l-utils`, `vulkan-tools`, `wireplumber`, `x11-xserver-utils`, and `xdg-utils`.

The default Live ISO list in `packaging/live-build/config/package-lists/uhdp.list.chroot` is: `live-boot`, `live-config`, `xfce4`, `lightdm`, `xserver-xorg`, `dbus-x11`, `firefox-esr`, `network-manager`, `network-manager-gnome`, `wpasupplicant`, `udisks2`, `policykit-1`, `sudo`, `util-linux`, `e2fsprogs`, `python3`, `python3-venv`, `python3-pip`, `python3-dev`, `build-essential`, `python3-psutil`, `python3-pyudev`, `python3-usb`, `python3-evdev`, `firmware-brcm80211`, `firmware-iwlwifi`, `firmware-linux-nonfree`, `firmware-misc-nonfree`, `firmware-realtek`, `smartmontools`, `nvme-cli`, `lshw`, `pciutils`, `usbutils`, `dmidecode`, `lm-sensors`, `v4l-utils`, `alsa-utils`, `evtest`, `libinput-tools`, `bluez`, `rfkill`, `iproute2`, `ethtool`, and `x11-xserver-utils`.

The Live build requires a Debian 13 (trixie) amd64 host, `live-build`/`lb`, and npm. Its hook creates an isolated Python venv and installs the entire root `requirements.txt`, then purges build tools; the appliance therefore also receives pytest and the flat transitive pins. The apt `python3-psutil`, `python3-pyudev`, `python3-usb`, and `python3-evdev` packages overlap libraries installed into that isolated venv and may be redundant. The generic Linux installer package list is broader than the Live ISO list. Utilities catalogued/checked by the launcher but not explicitly included in the Live ISO list include examples such as `fio`, `stress-ng`, `memtester`, `iperf3`, `iw`, `upower`, `acpi`, `edid-decode`, `glmark2`, `vulkan-tools`, `fwupd`, and `tpm2-tools`. Availability checks do not prove that a corresponding diagnostic is integrated; the launcher says so explicitly. No ISO was built or booted during this audit.

### Supabase and cloud architecture review

Supabase is **not required** for the Phase 1 local/offline application. The local app can use its file or SQLite repositories; SQLite is Python's standard-library `sqlite3`. Cloud sync is a separate opt-in path: `SyncWorker` runs with `STORAGE_BACKEND=sqlite` when `CLOUD_API_URL` and `CLOUD_STATION_TOKEN` are configured and sends outbox events to the repository's independent FastAPI cloud service.

`STORAGE_BACKEND=supabase` is an optional, custom PostgREST adapter (`app/persistence/supabase_store.py`) implemented with Python's standard-library `urllib`; no Supabase Python package is declared. It expects a configured generic `uhdp_records` table with `record_type`, `id`, `payload`, and `updated_at` fields, and a server-side service-role key. No Supabase DDL/migration for that table exists in the repository. The adapter does not use Supabase Auth, Storage, Realtime, or a client SDK. There is no `@supabase` frontend dependency.

This direct Supabase path is not feature-equivalent to local SQLite: evidence endpoints require SQLite; `SupabaseReportRepository` upserts the latest JSON/HTML record and does not implement `list_revisions()` or `finalize_revision()`; therefore the local report-history/finalization contract is not supported there. The service-role adapter is not a tenant authorization boundary and must not be exposed as a client credential. The repository's separate cloud SQL migrations define company-scoped tables, while custom cloud API code authenticates users/stations and applies company scoping. No `CREATE POLICY` or `ENABLE ROW LEVEL SECURITY` statements were found in the checked cloud migrations; direct database/PostgREST exposure must not be assumed protected by those API checks.

Recommendation: keep Supabase out of the Phase 1 required stack. Before adopting either cloud path, choose and validate one integration, define the required schema and tenant/access controls, implement parity for evidence and report revisions, and run live integration/backup/restore checks. **Live Supabase/cloud behavior has not been tested; no cloud readiness is claimed from JSON payload inspection.**

### Recommendations (no implementation performed)

| Priority | Recommendation |
|---|---|
| P1 — Phase 1 gate | Add an explicit, approved technician asset-resolution decision to the QC workflow before claiming asset identity is complete. Current UI callers omit both identity fields and leave normal QC sessions unresolved; do not auto-merge weak identifiers. |
| P1 — report governance | Treat local supersession actor fields as audit labels only until local API authentication/authorization exists. Do not describe a caller-supplied/fallback actor as an authorized correction. |
| P1 — cloud | Do not enable the Supabase adapter or cloud sync for production until live schema, tenant isolation/RLS or equivalent access controls, evidence, report revisions, and restore behavior are validated. Supabase itself is optional, not a Phase 1 requirement. |
| P2 — dependency hygiene | Separate runtime and test dependencies and create a reproducible Python test/deployment lock strategy; specifically review undeclared `pytest-asyncio`/test-client support, the unused PyYAML pin, optional pyusb/evdev, and the cloud transitive graph. Do not remove or add packages without a separately approved implementation. |
| P2 — deployment | Reconcile the Live ISO package list with the capability catalog and verify the image on Debian 13 hardware before claiming those diagnostic capabilities. Review duplicated apt Python modules and test-only packages in the Live venv. |
| P2 — releases | Consider in-range Python/npm patch updates only after focused/full tests. Treat Vite 8, TypeScript 7, React plugin 6, and Node typings 26 as major compatibility work, not routine updates. No package update/removal was performed. |

### Validation results

- Full backend: `python -m pytest -q` — **475 passed, 5 failed, 19 warnings**. The two documented API failures are `tests/api/test_diagnostic_session_routes.py::test_execute_single_diagnostic` and `tests/api/test_diagnostic_session_routes.py::test_station_profile_retest_and_qa_disposition_persist_in_report`; the other three are the baseline-reproduced empty-action workflow tests above.
- Frontend: `npm --prefix frontend run build` — **passed** with Vite 7.3.7 (2285 modules transformed).
- Dependency checks: `pip check` — **No broken requirements found**; `npm audit` — **0 vulnerabilities**; OSV — **0 advisories across 37 pinned Python packages**.
- Workflow baseline comparison: baseline and current each **3 failed, 4 passed** for `tests/api/test_workflows.py` under matched temporary data/configuration.
- Migration/identity/revision tests ran as part of the full backend suite and passed; all migration test databases/data were temporary. No production migration ran.
- `git diff --check` — **passed** after this documentation update; the frontend build created only its ignored `frontend/dist` output.

**Files changed by this audit:** `docs/UHDP_BACKEND_AUDIT.md` only. No dependency, lockfile, schema, frontend, or application code was changed. No cloud synchronization, Phase 2 work, or commit/push was performed.

## Phase 1 final corrections — technician asset resolution and local reopen authorization

This addendum records the approved corrections to the two remaining Phase 1 gaps. The earlier recommendation and validation statements above describe the audit checkpoint, not this subsequent implementation.

### Technician asset resolution

New technician intake now requires an explicit choice: link an existing asset by ID, create a new asset, or continue unresolved. Existing IDs are suggested from persisted QC sessions; the backend still performs exact-ID lookup and rejects unknown IDs. New assets are sent only with `create_asset=true`. The unresolved choice sends `create_asset=false`, creates no asset, and displays a warning. The technician workflow context identifies the linked asset ID or visibly marks identity unresolved.

The standalone manual-inspection creator follows the same three-way choice. Session-context session creation now requires an explicit asset-resolution choice, and recovery of a pending session loads an existing record rather than silently creating an unresolved one. Existing sessions cannot have their asset identity changed from intake. The backend preserves retest source identity (including unresolved legacy identity) and rejects conflicting explicit asset IDs. No hardware fingerprinting or automatic asset matching was added.

### Local reopen authorization and audit

The local reopen endpoint now requires the actual TCP peer to be loopback and a locally provisioned supervisor credential. It reads only `request.client.host`; forwarded headers do not participate. Missing or malformed configuration fails closed, incorrect credentials are rejected, and five failed attempts within five minutes trigger a ten-minute per-peer lockout. The in-memory throttle is bounded to 256 peer entries. Remote requests are rejected even with a valid credential.

Credentials are never stored in browser storage, session data, audit payloads, or logs. The frontend clears its password input after every submission. The required actor label is stored only as an asserted audit attribution; it is not treated as an authenticated identity. Authorization proves possession of a shared supervisor credential, **not the real-world identity of the person entering the label**.

Credential provisioning and rotation are performed locally on the Linux deployment host from the repository root:

```text
DATA_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/uhdp" \
  .venv/bin/python scripts/provision_local_supervisor_credential.py
```

The command prompts twice for a credential of at least 12 characters, generates a random 16-byte salt, and writes only the salted hash to `$DATA_DIR/local_auth/supervisor.credential`. The hash uses PBKDF2-HMAC-SHA256 with 310,000 iterations and a 32-byte derived key. Provisioning atomically replaces the hash, enforces directory mode `0700` and file mode `0600`, and refuses to run on non-POSIX systems where these permissions cannot be enforced. The backend verifies ownership and permissions and fails closed on a malformed or insecure credential file. Restart the backend after initial provisioning or rotation. To rotate, run the same command with the replacement credential; the old hash is replaced.

For the Live USB, first start the Live launcher so it mounts the `UHDP_DATA` partition, then run this from a second terminal:

```bash
data_device="$(readlink -f /dev/disk/by-label/UHDP_DATA)"
mountpoint="$(findmnt -rn -S "$data_device" -o TARGET)"
DATA_DIR="$mountpoint/uhdp-data" \
  /opt/uhdp/.venv/bin/python /opt/uhdp/scripts/provision_local_supervisor_credential.py
```

The Live image includes the provisioning script and stores its hash on the persistent data partition. Do not copy the hash or credential into source control or support logs.

Reopen attempts reuse the existing SQLite `audit_events` table from migration `0002_domain_evidence.sql`; no schema or production migration was added. The route opens only an already-initialized database and does not run migrations; if the database or audit table is unavailable, reopening fails closed. Events persist session ID, asserted actor label, action, outcome, authorization basis, reason where applicable, and timestamp. The route records an authorization event before changing session state and a success/failure outcome after the operation. Reopening does not generate a report revision or edit a finalized revision. Any later QC data edit follows the existing explicit report supersession flow.

Supported UHDP launch paths disable Uvicorn proxy-header processing (`--no-proxy-headers`), so the route's `request.client.host` check uses the socket peer rather than forwarded client headers. This applies to the Linux and Live launchers, the documented direct development commands, and the container command. Custom launch commands must retain this option for the same peer-address guarantee.

### Validation and limitations

- Focused backend: `python -m pytest tests/api/test_local_reopen_authorization.py tests/api/test_diagnostic_session_routes.py tests/api/test_reports_api.py -q -k "not test_execute_single_diagnostic and not test_station_profile_retest_and_qa_disposition_persist_in_report"` — **37 passed, 2 deselected**. This covered asset resolution, retest preservation/conflict behavior, legacy unresolved identity, reopen authorization/audit, and report behavior.
- Frontend: `npm --prefix frontend run build` — **passed** with Vite 7.3.7 (2286 modules transformed). There is no configured frontend component-test runner; technician UI callers were updated for intake, standalone manual inspection, session-context starts, and pending-session recovery.
- Local reopen authorization tests cover unconfigured and malformed credentials, missing/wrong/correct submitted credentials, loopback and remote peers, forwarded-header spoofing, bounded throttling, audit persistence/redaction, and finalized report immutability.
- Full backend: `python -m pytest -q` — **489 passed, 2 failed, 19 warnings**. The only failures were the two previously documented unrelated API failures: `test_execute_single_diagnostic` (`/complete` returns `checks_complete`, expected `completed`) and `test_station_profile_retest_and_qa_disposition_persist_in_report` (`CONDITIONAL PASS` returns 422). The three empty-action workflow failures documented earlier did not fail in this full-suite run; no workflow code was changed.
- `git diff --check` — **passed**. Backend Python compilation checks passed. The Linux-only credential provisioning command was not run in this Windows development environment; its POSIX-only guard prevents claiming that filesystem permissions were exercised here.
- SQLite audit events use the existing migration/table; there are no schema changes or production migrations.
- The shared credential is a local offline authorization boundary, not individual sign-in or accountability. A person with local machine access can use the credential; compromise of the host or browser is outside this mechanism. Throttle state resets when the backend restarts. Credential-file protection depends on the deployment filesystem honoring directory mode `0700` and file mode `0600`.
- Audit persistence requires the existing SQLite `audit_events` table to have been initialized. The endpoint does not migrate or create a missing database; a reopen attempt in a configuration without that existing local audit store is rejected.
- No cloud authentication, Supabase synchronization, or live cloud behavior was tested. No cloud readiness is claimed.
- No Phase 2 work or unrelated API fixes were performed. No dependencies, manifests, lockfiles, database schemas, or production data were changed.

## Linux Phase 1 runtime corrections

This addendum corrects the Live and regular Linux runtime findings identified
after the preceding Phase 1 review. It does not start Phase 2 or change the
database schema.

### Live asset and audit storage

`scripts/run_uhdp_live.sh` now selects `STORAGE_BACKEND=sqlite` and invokes the
existing legacy importer against the persistent session and report directories
before starting Uvicorn. The import is idempotent and inserts only records not
already present; original JSON files are retained. The persistent
`uhdp.sqlite3` is the canonical store for new sessions, assets, reports, and
reopen audit events. New writes do not dual-write to the legacy JSON paths.
Report revision renderings continue to use the existing `DATA_DIR/Reports`
storage. SQLite initialization applies the existing migrations and creates the
existing audit table before the reopen endpoint can receive a request. No
migration or data rewrite was added.

### Linux launcher and session ID retries

`scripts/run_uhdp_linux.sh` now serves the already-built UI with the existing
Python static server instead of invoking Vite Preview. It keeps the existing
loopback API/UI listeners, API and UI health checks, static asset handling,
and SPA fallback; runtime no longer requires Node.js, Vite, or `node_modules`.
Frontend build dependencies remain necessary when producing the build output.

Reusing a session ID remains idempotent when an explicitly supplied asset
identity matches the stored session. Explicitly conflicting asset IDs or
asset-resolution choices return HTTP 400. Legacy requests that omit
`asset_id` and `create_asset` remain idempotent and do not alter the stored
identity. An explicitly supplied `create_asset=false` conflicts with an
already-linked session when no matching `asset_id` is also supplied.

### Supervisor credential provisioning

Provisioning now refuses to overwrite an existing credential by default.
Rotation requires `--rotate` and the operator must type `ROTATE`. Initial
creation uses an atomic no-overwrite link; rotation writes a same-directory
temporary file and atomically replaces the old file only after confirmation.
The hash is never printed. The existing PBKDF2-HMAC-SHA256 derivation and
random salt are unchanged, as are the restrictive directory/file modes
(`0700`/`0600`). Interrupted rotation leaves the previous credential intact.

### Tests and validation

Added coverage in `tests/persistence/test_identity_foundation.py` for importing
retained legacy JSON into configured SQLite storage, existing/new asset
resolution, unresolved and retest identity, and legacy session/report reads.
`tests/api/test_diagnostic_session_routes.py` now covers session-ID replay and
conflicting identity fields. `tests/api/test_local_reopen_authorization.py`
checks successful audit persistence across reopening the SQLite database.
Launcher source checks and static server missing-build/SPA/asset tests are in
`tests/scripts/test_linux_runtime_scripts.py` and
`tests/scripts/test_live_ui_server.py`. POSIX provisioning tests cover first
creation, overwrite refusal, deliberate rotation, permissions, and failed
atomic replacement.

Validation ran on the current **Windows** host only:

```text
.\.venv\Scripts\python.exe -m pytest tests\api\test_diagnostic_session_routes.py tests\api\test_local_reopen_authorization.py tests\persistence\test_identity_foundation.py tests\scripts\test_live_ui_server.py tests\scripts\test_linux_runtime_scripts.py tests\scripts\test_provision_local_supervisor_credential.py -q -k "not test_execute_single_diagnostic and not test_station_profile_retest_and_qa_disposition_persist_in_report"
59 passed, 4 skipped, 2 deselected

.\.venv\Scripts\python.exe -m pytest -q
496 passed, 2 failed, 4 skipped, 19 warnings
```

The two full-suite failures remain the documented unrelated API failures:
`test_execute_single_diagnostic` expects `/complete` status `completed` but
receives `checks_complete`, and
`test_station_profile_retest_and_qa_disposition_persist_in_report` rejects
`CONDITIONAL PASS` with HTTP 422. They were not changed. The four skipped tests
are the POSIX credential-provisioning tests, which cannot validate Linux file
permissions on this host.

```text
npm --prefix frontend run build
passed; Vite 7.3.7 transformed 2286 modules

git diff --check
passed
```

No actual Linux runtime test, Linux ISO build, physical USB boot, or
restart-on-Live-media test was performed. The Linux launch scripts were
inspected and their source-level tests ran on Windows; that is not Linux
validation. Linux credential creation/rotation, importer startup on the Live
image, loopback listener behavior, audit persistence across a real application
restart, and ISO/physical boot remain unverified. Live cloud behavior remains
untested; no cloud readiness is claimed.
