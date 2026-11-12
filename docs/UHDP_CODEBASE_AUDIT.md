# UHDP Codebase Audit — Senior Developer Review

**Commit audited:** `771969b` (`feature/phase2-diagnostics`, 6 commits ahead of `origin/main`, not pushed)
**Scope:** `app/`, `cloud/`, `frontend/`, `tests/`, `scripts/`, packaging and CI
**Method:** static review, route enumeration, dependency and config inspection, full test run, Python compile check, TypeScript typecheck, npm audit
**Not performed:** live load testing, penetration testing, Docker image build, coverage measurement

> Threat-model note: this is a **local technician appliance**, not an internet service. I grade security against both "strictly loopback, single trusted user" and "reachable by another LAN host or browser". Several findings are acceptable only under the first model.

---

## 1. Executive summary

The codebase is substantial (~23k Python LOC, ~16k frontend LOC, 563 passing tests) and shows real engineering discipline in persistence, audit trails, and the local supervisor credential flow. It is **not a rewrite candidate**. The main risks are not algorithmic correctness — they are **deployment portability, unauthenticated destructive APIs, missing CI, and legacy duplication**.

| Area | Rating | Rationale |
|---|---|---|
| Correctness | **B** | Tests pass; domain rules are well enforced; some state/concurrency gaps |
| Security | **D+** | Only one endpoint is authenticated; destructive operations are open; Docker exposure |
| Reliability | **C+** | Good SQLite/outbox/evidence design; shutdown and concurrency gaps |
| Testing | **B−** | Broad pytest suite; no CI, no frontend tests, no tests for newest features |
| Maintainability | **C** | Several parallel implementations and dead modules; no lint/type gate |
| Deployment/Ops | **C−** | Python-version bug, Docker secret/bloat risk, config drift |
| Frontend | **B−** | Strict TS, no `any`, clean build; monoliths, no lint/tests, hardcoded API |
| Cloud service | **B** | Good tenant scoping, idempotency, hashing; no login rate limit/connection pool |
| Documentation | **A−** | Unusually good architecture and phase docs |

**Top 5 risks**

1. **Unauthenticated destructive API** — 68 operations, only `/reopen` has a credential.
2. **Installer accepts Python 3.10, code requires 3.11+** — installs a non-starting app on Ubuntu 22.04.
3. **Docker build copies the whole checkout, including `.env` and `.venv`**, and runs as root.
4. **No CI executes tests/typecheck/build** — the current 6-commit feature branch has never been CI-validated.
5. **File-backend report HTML is unescaped** (stored XSS) and file repositories lack path/atomic-write hardening.

---

## 2. Verification performed

```text
pytest -c app/pytest.ini tests -q ........ 563 passed, 37 warnings in 33.17s
python -m compileall app cloud scripts .... clean
tsc --noEmit (frontend) ................... exit 0
pip check ................................. no broken requirements
npm audit --omit=dev ...................... 0 vulnerabilities (311 deps)
OpenAPI route enumeration ................. 68 operations / 60 paths, no duplicates
```

Warnings are minor: deprecated `datetime.utcnow()` in legacy report tests, and a `Device.properties` deprecation in demo tests.

---

## 3. Findings

| ID | Severity | Area | Finding |
|---|---|---|---|
| SEC-1 | **High** | Security | All state-changing/destructive endpoints are unauthenticated; Docker/compose expose them on `0.0.0.0` |
| DEP-1 | **High** | Deployment | Installer allows Python 3.10 but code needs 3.11+ (`datetime.UTC`, `StrEnum`) |
| SEC-2 | **High** | Security/Ops | No `.dockerignore`; `COPY . .` can ship `.env`, `.venv`, `node_modules`, `data`; container runs as root |
| QA-1 | **High** | Process | No test/build CI; current branch unpushed, so CodeQL-on-`main` never sees it |
| SEC-3 | **Medium** | Security | File-backend report HTML is unescaped → stored XSS via client-controlled device/intake data |
| BUG-1 | **Medium** | Reliability | Global in-memory session cache + singleton services are not thread/multi-worker safe |
| BUG-2 | **Medium** | Reliability | `DiagnosticJobService` is never shut down; running stress jobs can hang shutdown or orphan subprocesses |
| ARCH-1 | **Medium** | Maintainability | Multiple parallel diagnostic/report/session implementations plus dead modules |
| OPS-1 | **Medium** | Config | Dead settings (`HOST`, `PORT`, `LOG_LEVEL`, timeouts, scan intervals); backend default `file` contradicts launcher `sqlite` |
| DATA-1 | **Medium** | Data integrity | File repositories use raw IDs in paths and non-atomic writes; one corrupt JSON breaks listing |
| PERF-1 | **Medium** | Performance | Discovery on every `/devices`; migrations on every `SQLiteDatabase()`; synchronous diagnostics in request threads |
| CLOUD-1 | **Medium** | Cloud | No login rate limiting; unbounded event payloads; new DB connection per request |
| OPS-2 | **Medium** | Data lifecycle | Revisions, outbox, evidence, and job files grow without retention/backup policy |
| QA-2 | **Medium** | Testing | Zero tests for evidence upload/download and storage benchmarks |
| QUAL-1 | **Medium** | Tooling | No `pyproject.toml`, linter, formatter, pre-commit, or Python typecheck |
| SEC-4 | **Low** | Security | `/ws` accepts any Origin (WebSocket is not protected by CORS) |
| SEC-5 | **Low** | Security | `x-uhdp-confirmed: true` header is used as a safety gate but is trivially spoofable |
| SEC-6 | **Low** | Security | Static UI server has no security headers and serves directory listings under `dist/assets/` |
| QUAL-2 | **Low** | Code quality | 1,841-line session service, 988-line display page; private attribute access (`service._service.registry`) |
| HYG-1 | **Low** | Repo hygiene | Tracked `project_tree.txt` (UTF-16 Windows dump), `temp_scheduler_test.py`, commented route imports, duplicate `typing` import |
| DOC-1 | **Low** | Governance | No `LICENSE`, `SECURITY.md`, or `CONTRIBUTING.md` |

---

## 4. Detailed findings

### SEC-1 — Unauthenticated destructive API (High)

**Evidence**
- `app/main.py:92-120` registers all routers with no auth dependency.
- Route enumeration: **68 operations**, including:
  - `POST /storage-benchmarks/` — writes a **2 GiB** file (`storage_benchmark_service.py:22`), any mounted local filesystem.
  - `POST /diagnostic-jobs/` — spawns CPU/GPU stress subprocesses up to **1 hour** (`MAX_CPU_STRESS_SECONDS`).
  - `POST /evidence/{session_id}` — writes up to 100 MiB per upload.
  - `DELETE /diagnostic-sessions/{session_id}`, `DELETE /storage-benchmarks/{id}`, `DELETE /workflows/{id}`.
  - `POST /diagnostics/{diagnostic_type}` and `POST /diagnostic-sessions/{id}/execute` — run local hardware tests.
- Only `POST /diagnostic-sessions/{id}/reopen` is protected (`app/api/sessions/diagnostic_routes.py:487`, `app/core/local_reopen_auth.py`).
- `app/core/config.py:17` defaults `HOST=0.0.0.0`; `Dockerfile:6` binds `0.0.0.0`. The Linux launcher correctly binds `127.0.0.1` (`scripts/run_uhdp_linux.sh:251`), but Docker and ad-hoc `uvicorn ... --host 0.0.0.0` do not.
- `POST /evidence/{id}` accepts `x-uhdp-confirmed: true` as its only gate (`app/api/evidence.py:46`).

**Impact**
- LAN neighbor or any local process can start stress tests, write/delete files, delete sessions, and trigger diagnostics.
- CORS limits browser *reads*, but simple cross-origin POSTs (endpoints with no JSON body) and WebSockets are not fully mitigated. A malicious page visited by the technician can trigger state changes; DNS rebinding can weaken the loopback assumption.
- The inconsistency is notable: reopen uses strong PBKDF2 + loopback + lockout, while everything else is open.

**Remediation**
1. Bind loopback by default everywhere (Docker too), and require an explicit opt-in for LAN exposure.
2. Add a local API token or reuse the supervisor credential as a station bearer token for all state-changing routes.
3. Validate `Host` and `Origin` for every mutating request; add a CSRF header requirement.
4. Validate `Origin` on `/ws`; reject unknown origins.
5. Add an auth dependency at the router-inclusion level so new endpoints cannot be added unprotected.

---

### DEP-1 — Python 3.10 is advertised but unsupported (High)

**Evidence**
- `scripts/install_linux.sh:96` rejects only `< 3.10`.
- Code uses 3.11-only APIs: `from datetime import UTC` in **28 files**, and `enum.StrEnum` in `app/plugins/capabilities.py` and `app/workflows/execution/execution_status.py`.
- Ubuntu 22.04 ships Python 3.10; the installer installs `python3` (`scripts/install_linux.sh:58`).

**Impact**
On a stock Ubuntu 22.04 target, installation succeeds but the backend fails immediately with `ImportError: cannot import name 'UTC'`. This directly contradicts the Linux install path in the README.

**Remediation**
- Raise the check to 3.11 (preferably 3.12 to match the Docker image), or replace `datetime.UTC`/`StrEnum` with 3.10-compatible equivalents.
- Add a CI matrix for the minimum supported interpreter.
- Record the version in a `pyproject.toml`/`.python-version`.

---

### SEC-2 — Docker build context and root user (High)

**Evidence**
- No `.dockerignore` exists.
- `Dockerfile:5` uses `COPY . .`.
- The local repo contains `.env`, `.venv/`, `frontend/node_modules/`, `frontend/dist/`, `data/`, `.git/`, `logs/`.
- `Dockerfile` has no `USER` directive.

**Impact**
- `.env` is copied into an image layer, leaking `SUPABASE_SERVICE_ROLE_KEY`, `CLOUD_STATION_TOKEN`, and JWT/database secrets if a developer ever builds locally or CI uses a provisioned checkout.
- Image size and attack surface balloon; build cache is invalidated by unrelated runtime files.
- Root container increases blast radius for the unauthenticated API.

**Remediation**
```text
.env
.env.*
.venv/
.git/
data/
logs/
frontend/node_modules/
frontend/dist/
tests/
docs/
__pycache__/
.pytest_cache/
```
Add a non-root user, `COPY` only required paths, and use a multi-stage build for the frontend.

---

### QA-1 — No CI for tests, types, or build (High process risk)

**Evidence**
- `.github/workflows/` contains only `codeql.yml` and `summary.yml`.
- CodeQL runs on `main` and PRs to `main` only.
- Current branch `feature/phase2-diagnostics` has **no upstream** and 6+ commits not on `origin/main`.
- The suite is fast (**33s**), so a CI job is cheap.

**Impact**
- The branch containing Phases 1–4 has never been validated by CI.
- Regressions rely on developers remembering to run pytest/tsc.
- CodeQL will not analyze the unpushed branch.

**Remediation**
Add one workflow:
```text
ruff check app cloud tests
pytest -c app/pytest.ini tests -q
tsc --noEmit (frontend)
vite build (frontend)
npm audit --omit=dev
```
Run on every branch and PR. Add `pip-audit` and a Python 3.11/3.12 matrix.

---

### SEC-3 — Stored XSS in file-backend report HTML (Medium; High if file backend is used)

**Evidence**
- `app/workflows/reporting/file_report_repository.py:200-228` builds HTML with raw f-string interpolation:
  - `report.report_id`, `report.device_id`, `report.status`, `report.created_at`
  - `json.dumps(report.data)` inside `<pre>`
- `report.device_id` is client-controlled: `PUT /diagnostic-sessions/{id}/intake` assigns `session["device_id"] = request.device_id` (`diagnostic_session_service.py:323`) and refreshes the report.
- The frontend links directly to this endpoint: `frontend/src/api/reports.ts:60-61`.
- The SQLite path is safe: `app/persistence/local/repositories.py:160-176` uses `html.escape`. The unescaped builder is the file backend.

**Impact**
A technician-entered device ID or intake value containing `<script>`/`<img onerror=...>` executes when the HTML report is opened, on the API origin. Since the API is unauthenticated (SEC-1), that script can delete sessions or start benchmarks. Reports are also intended for export/sharing, widening exposure.

**Remediation**
- Escape every interpolation in `FileReportRepository._build_html` (reuse `HtmlReportGenerator` or `html.escape`).
- Add a regression test asserting `<script>` is neutralized.
- Apply the same review to any future HTML renderer.

---

### BUG-1 — Process-global session cache is not concurrency-safe (Medium)

**Evidence**
- `diagnostic_session_service = DiagnosticSessionService()` at module import (`diagnostic_session_service.py:1840`).
- `self._sessions = {}` (`:73`), populated at `:243`, read/cached at `:743-759`.
- Mutating flows read the dict, mutate, refresh report, then save — with no per-session lock (only `_display_lock` exists).
- Cache entries are never evicted except on delete; `list_sessions()` reads the repository, so cache and repository can diverge.

**Impact**
- Concurrent requests (polling frontend + technician action, multiple tabs, multiple workers) can lose updates or persist partially refreshed reports.
- Memory grows with session count.
- Running with `uvicorn --workers > 1` is unsafe: each worker has its own cache and background services.

**Remediation**
- Add a per-session RLock or an optimistic revision check on save.
- Bound/evict the cache; treat the repository as source of truth.
- Document and enforce single-worker mode until shared state is externalized.

---

### BUG-2 — Diagnostic job service has no shutdown path (Medium)

**Evidence**
- `DiagnosticJobService` owns a `ThreadPoolExecutor(max_workers=2)` (`diagnostic_job_service.py:63`) and is instantiated globally at import (`:767`).
- No `shutdown()` method; `app/main.py` shutdown only stops storage benchmarks, sync worker, and runtime.
- CPU stress can run up to `MAX_CPU_STRESS_SECONDS = 3600`.

**Impact**
On shutdown/restart during a stress test, the process can block on non-daemon executor threads or terminate while leaving the `stress-ng`/GPU child process running. Job state is persisted and recovered, but the child process is not.

**Remediation**
- Add `shutdown()` that sets all cancellation events, terminates child processes, and calls `executor.shutdown(wait=True, cancel_futures=True)`.
- Register it in the FastAPI lifespan next to `shutdown_service()`.
- Consider a job supervisor that owns subprocesses explicitly.

---

### ARCH-1 — Parallel implementations and dead modules (Medium)

**Evidence**
- Diagnostic execution has at least three entry paths:
  - `app/hal/diagnostic_service.py`
  - `app/runtime/services/diagnostic_service.py` (exposed via `app/api/routes/diagnostics.py`)
  - `app/services/diagnostic_session_service.py`
- Session handling has `app/services/session_service.py` (in-memory) and `DiagnosticSessionService`.
- Reporting has `app/reports/` and `app/workflows/reporting/`, both exposed (`/reports/{id}` and `/reports/export/{id}`).
- Dead/unreferenced modules: `app/api/diagnostic_sessions.py`, `app/api/diagnostics.py`, `app/api/websocket.py` (shadowed by the `websocket/` package), `app/base.py`, `app/equals_condition.py`.
- `app/api/devices.py:1-3` has a duplicate `from typing import Any`.
- `app/main.py` contains commented-out router registration.

**Impact**
New contributors cannot tell which path is authoritative; fixes must be applied twice; dead code hides real behavior and confuses security review.

**Remediation**
- Nominate one public use-case boundary per operation and delete/delegate the rest.
- Add a short ADR mapping each endpoint to its service and persistence backend.
- Remove dead modules and commented imports in a dedicated cleanup commit.

---

### OPS-1 — Configuration drift and dead settings (Medium)

**Evidence**
- `HOST`, `PORT`, `SESSION_TIMEOUT_MINUTES`, `DEVICE_SCAN_INTERVAL_SECONDS`, `WEBSOCKET_HEARTBEAT_SECONDS`, and `DEFAULT_REPORT_FORMAT` have **zero consumers** outside `config.py`.
- `LOG_LEVEL` is ignored: `setup_logging()` hardcodes `root.setLevel(logging.INFO)` (`app/core/logging.py:13`).
- Backend default is `STORAGE_BACKEND="file"` (`config.py:28`), while `.env.example` and the launcher default to `sqlite`.
- Frontend API base is hardcoded to `:8000` (`frontend/src/api/client.ts:7`).
- `setup_logging()` writes to a **relative** `logs/` directory, not `DATA_DIR`.

**Impact**
Operators change settings that do nothing; running directly with `uvicorn` silently uses the legacy file backend; deployments behind a proxy or different port require code edits.

**Remediation**
- Delete or implement every setting; validate `LOG_LEVEL` with the logging enum.
- Make `file` an explicit legacy opt-in; default to `sqlite`.
- Use `VITE_API_BASE_URL` with a sensible fallback; support same-origin `/api`.
- Put logs under `DATA_DIR/logs` or a system log directory.

---

### DATA-1 — File repositories lack path and atomic-write hardening (Medium)

**Evidence**
- `app/services/file_session_repository.py:24-28, 42-46, 60-64` uses `session_id` directly in `f"{session_id}.json"`; no safe-component validation.
- `app/workflows/reporting/file_report_repository.py:135, 197-198, 236-255` uses `report_name` directly in paths.
- `app/reports/report_storage.py:34-41, 79-101` does the same.
- Writes use `open(..., "w")` without temp-file + `os.replace`; a crash mid-write corrupts state.
- `list_all()`/`list_reports()` fail the whole listing if one JSON file is corrupt.
- By contrast, `app/persistence/local/report_files.py:14, 28` validates IDs and writes atomically — the right pattern exists but is not reused.

**Impact**
Under the file backend: latent path traversal if a caller ever passes an unvalidated ID, torn files on power loss, and one bad file breaking history/report lists. HTTP routing currently blocks encoded slashes in most path params, so this is primarily defense-in-depth and direct-service risk.

**Remediation**
- Apply a shared `_safe_component` to every file-backed repository.
- Reuse the atomic-write helper from `LocalReportFiles`.
- Skip/quarantine unreadable files instead of aborting the listing.

---

### PERF-1 — Avoidable per-request work (Medium)

**Evidence**
- `GET /devices/` calls `discovery_service.discover()` on every request (`app/api/devices.py:66-75`), which runs multiple `subprocess` probes.
- Every `SQLiteDatabase()` construction runs `_migrate()` and inserts a boot-session row (`database.py:27-45`); many request handlers create a fresh instance (e.g., `app/api/evidence.py:29`, `app/api/sync.py`).
- `execute_diagnostic` runs hardware tests synchronously inside the request (`diagnostic_session_service.py:761-841`), consuming a threadpool worker.
- `EvidenceStorage.open()` re-hashes the entire file on every download (`evidence/storage.py:106-123`), up to 100 MiB.

**Impact**
Slow UI under repeated polling, unnecessary SQLite writes, threadpool starvation under concurrent requests, and slow evidence downloads.

**Remediation**
- Cache discovery for a short TTL or push discovery to a job.
- Create one process-wide `SQLiteDatabase` and reuse it; run migrations once at startup.
- Route long diagnostics through the existing job service.
- Verify evidence integrity once at write/first access and cache the result, or stream-verify with a bounded design.

---

### CLOUD-1 — Cloud service hardening gaps (Medium)

**Evidence**
- `POST /v1/auth/login` (`cloud/api.py:42-70`) has no rate limiting or lockout; PBKDF2 alone doesn't stop online guessing.
- `EventBatch.events: list[dict[str, Any]]` has a 100-count limit but no per-event size limit; payloads are stored as JSONB.
- `CloudDatabase.connection()` opens a new psycopg connection per request (`cloud/database.py:23-35`); no pool.
- Positive: tenant scoping is consistently applied, station tokens are SHA-256 hashed, JWT is short-lived and signature-checked, sync events are idempotent, and evidence upload verifies checksum and size.

**Impact**
Credential stuffing/brute force, memory/DB amplification via large payloads, and connection churn under load.

**Remediation**
- Add per-IP/company login throttling and a small failed-attempt window.
- Cap event/payload bytes and total batch bytes.
- Add `psycopg_pool.ConnectionPool`.
- Add refresh-token/revocation design if sessions outlive the 15-minute token.

---

### OPS-2 — No data retention or backup policy (Medium)

**Evidence**
- Session/report revisions are append-only (`session_revisions`, `report_revisions`).
- Outbox events accumulate until acknowledged; failed events remain for manual retry.
- Evidence files and `diagnostic_jobs/*.json` are never pruned.
- No backup/restore script or documented retention window.

**Impact**
Disk exhaustion on long-lived stations; slow queries and listings over time; no recoverability story for the SQLite database or evidence tree.

**Remediation**
- Define retention (sessions, revisions, synced outbox, jobs, evidence) and implement a scheduled compaction job.
- Add documented backup/restore for `uhdp.sqlite3` + evidence directory.
- Alert on low free space before benchmarks/evidence uploads.

---

### QA-2 — Newest features are untested (Medium)

**Evidence**
- No test references `StorageBenchmark`/`storage_benchmarks` or `EvidenceStorage`/`/evidence`.
- Phase 4 (technician checks) added 1,040 lines with no accompanying tests.
- No frontend test runner or test files.

**Impact**
The most dangerous operations (2 GiB writes, 100 MiB uploads, path handling) are the least tested; regressions will not be caught by CI even after CI is added.

**Remediation**
- Add API tests for upload size/media-type/confirmation, checksum mismatch, traversal attempt, and cleanup.
- Add service tests for benchmark target validation, free-space guard, cancellation, and file cleanup.
- Add a smoke test that asserts every registered route appears in OpenAPI and that mutating routes have the auth dependency.

---

### Lower-severity observations

- **SEC-4:** `/ws` (`app/api/websocket/routes.py:6-21`) accepts any origin and broadcasts job/runtime events. Validate `Origin` and authenticate the socket.
- **SEC-5:** `x-uhdp-confirmed` (`app/api/evidence.py:46`) is a UX hint, not a security control. Document it as such or remove it in favor of real auth.
- **SEC-6:** `scripts/serve_uhdp_ui.py` uses `SimpleHTTPRequestHandler`; `/assets/` returns a directory listing, and there are no CSP/`X-Content-Type-Options`/frame headers.
- **QUAL-1:** No `pyproject.toml`, Ruff/Black/ESLint/Prettier, pre-commit, or Python typecheck. Formatting and import ordering are inconsistent (e.g., `app/api/devices.py`).
- **QUAL-2:** Large files increase review risk: `diagnostic_session_service.py` 1,841 lines, `DisplayDiagnosticPage.tsx` 988, `Results.tsx` 704, `CosmeticInspection.tsx` 676. `app/api/routes/diagnostics.py:24` reaches into `service._service.registry`.
- **HYG-1:** Tracked junk: `project_tree.txt` (UTF-16 Windows tree dump), `temp_scheduler_test.py` (debug script), commented-out imports in `app/main.py`.
- **DOC-1:** No `LICENSE`, `SECURITY.md`, or `CONTRIBUTING.md`; add a vulnerability-reporting path before distributing the appliance.

---

## 5. What is genuinely well done

These deserve preservation, not rework:

- **Local reopen security** (`app/core/local_reopen_auth.py`): PBKDF2-SHA256 with 310k iterations, constant-time comparison, loopback-only, per-peer failure window and lockout, strict file ownership/permission checks. This is the strongest security component in the repo.
- **Evidence storage** (`app/evidence/storage.py`): sanitized filenames, confined resolved paths, `O_NOFOLLOW`, 0600 files, 0700 directories, fsync, SHA-256 verification on read, cleanup on metadata failure.
- **SQLite design**: WAL, foreign keys, `synchronous=FULL`, versioned migrations, append-only revisions, transactional outbox, boot sessions, and startup recovery tests.
- **Cloud tenant isolation**: company scoping on every query, hashed station tokens, short-lived HS256 tokens, idempotent event receipts, conflict preservation, checksum-verified presigned uploads.
- **Frontend baseline**: strict TypeScript, no `any`, no `dangerouslySetInnerHTML`, React escaping, route-level code splitting, vendor chunking.
- **Documentation**: architecture map, phase acceptance docs, Linux runbooks, and explicit security boundaries in `cloud/README.md`.
- **Test breadth**: 563 tests across API, HAL, discovery, workflows, persistence, reports, runtime, and scripts.

---

## 6. Recommended remediation plan

### P0 — next sprint

1. **Close the auth gap**: loopback default, router-level auth dependency, `Host`/`Origin` validation, WebSocket origin check, CSRF header for mutations.
2. **Fix Python compatibility**: require 3.11+ (prefer 3.12), update installer and docs, add CI matrix.
3. **Add `.dockerignore`, non-root user, and minimal build context.**
4. **Add CI** for pytest + tsc + build + lint on every branch/PR.
5. **Escape file-backend report HTML** and add a regression test.
6. **Add tests** for evidence and storage benchmarks.

### P1 — next 4–6 weeks

7. Add `pyproject.toml` with Ruff/mypy/pytest config; add ESLint/Prettier.
8. Implement `DiagnosticJobService.shutdown()` and register it in the lifespan.
9. Add per-session locking/revision checks; bound the session cache.
10. Reuse safe/atomic file helpers in all file repositories.
11. Add request IDs, structured logging, and basic metrics.
12. Add login rate limiting and payload limits to the cloud service; add a DB pool.

### P2 — next quarter

13. Consolidate duplicate diagnostic/report/session paths; delete dead modules.
14. Define retention/compaction and backup/restore runbooks.
15. Split the largest service/component files along clear boundaries.
16. Add security headers/CSP to the static server.
17. Add `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, and remove tracked scratch files.

---

## 7. Audit limitations

- No live server was started; findings are from source, route enumeration, and test execution.
- No coverage report was generated (`coverage`/`pytest-cov` not installed).
- No Docker image was built, so the `.dockerignore` finding is based on the absence of the file and the `COPY . .` instruction.
- No frontend runtime/accessibility testing; the audit covers build/type safety and code structure.
- Security findings assume the current implementation, not future changes on the unpushed Phase A branch.
