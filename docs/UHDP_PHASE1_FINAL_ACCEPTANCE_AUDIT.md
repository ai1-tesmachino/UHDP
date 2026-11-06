# UHDP Phase 1 Final Acceptance Audit (Ubuntu)

## Overall result

The backend suite, a real local API workflow, isolated SQLite persistence, legacy report migration, and the normal Linux launcher all passed the checks described below. **Phase 1 is not ready for acceptance.** CPU, memory, storage, and system diagnostics can label inventory or measurements as PASS without testing functional health; the bounded memory stress diagnostic also reports PASS without using its mismatch count. Physical-device testing and Live USB boot/reboot validation were not performed. Frontend page behavior was reviewed in source and the production UI was loaded in Chromium, but the technician workflow was not driven end to end through browser controls.

## Verification matrix

| Area | Result | Evidence | Remaining issue |
|---|---|---|---|
| Backend automated suite | **PASS** | On Ubuntu 26.04, ran `tmp=$(mktemp -d /tmp/uhdp-acceptance-suite.XXXXXX) && cp -a data "$tmp/data" && DATA_DIR="$tmp/data" ./.venv/bin/python -m pytest -c app/pytest.ini tests -q --tb=short`: **515 passed, 0 failed, 45 warnings**, no skips. | Passing tests do not establish physical hardware behavior or correct diagnostic PASS semantics. Warnings include existing deprecations. |
| Real API workflow | **PASS, limited scope** | Launched `uvicorn app.main:app` as a separate process with temporary SQLite paths. `/health/` returned healthy; `/devices/` returned 33 inventory records. Created a session and asset, saved intake, ran CPU diagnostics, saved a technician record, generated/retrieved a report, stopped the API, restarted it, and confirmed the session, asset, run, review, and report remained. | The API workflow only exercises the software path on this host. It is not a functional CPU or other hardware acceptance test. |
| SQLite and legacy migration | **PASS, isolated data** | Python SQLite `PRAGMA integrity_check` returned `ok` after restart and after migration. Importing a temporary copy of repository legacy reports imported 13; a second import added 0 and skipped 13. SHA-256 hashes of source JSON before and after matched. | The `sqlite3` CLI is unavailable; Python's SQLite module was used. No physical Live USB persistence test. |
| Frontend build and source review | **PARTIAL** | `cd frontend && npm run build` succeeded with Vite. `cd frontend && npm run` listed only `dev`, `build`, and `preview`; `frontend/**/*.{test,spec}.{js,jsx,ts,tsx}` matched no files. Source review covered the route tree and page components. The production static UI served at `127.0.0.1:3000`; headless Chromium rendered the root DOM (28,455 characters). | No frontend test suite exists. Browser smoke did not exercise technician interactions, every route, failure states, or navigation/refresh behavior against the real backend. |
| Diagnostic result correctness | **FAIL** | The real API full core workflow (`cpu`, `memory`, `storage`, `network`) returned HTTP 200 and `workflow_status=success`, with a report summary of **3 passed, 1 inconclusive**. CPU, memory, and storage result records had raw `passed` and no `evaluation` object; network was inconclusive. Code review confirms the CPU evaluator passes on a positive physical-core count, memory passes on a positive installed capacity, and storage passes on a non-empty mounted-volume inventory. | These are measurements/inventory, not functional health tests. `memory_stress_diagnostic.py` also records `pattern_mismatches` but unconditionally returns PASS after the readback loop; cancellation breaks can likewise proceed to PASS. This must be resolved before accepting functional results. |
| Normal Ubuntu launcher | **PARTIAL** | Ran the real `scripts/run_uhdp_linux.sh --no-browser` from an isolated temporary working copy with temporary `DATA_DIR`/`XDG_STATE_HOME`. API and bundled UI health checks passed at `127.0.0.1:8000` and `127.0.0.1:3000`; 13 legacy reports imported; SQLite integrity was `ok`; after SIGTERM both listener ports closed. Launcher/configuration tests are included in the passing backend suite. | `scripts/install_linux.sh` was not run: it installs OS packages, creates/replaces the virtual environment, installs npm dependencies, and configures autostart. The `.env` file exists but its contents were not inspected; the launcher runtime check used explicit temporary paths and did not validate the live `.env` settings. |
| Linux Live USB | **NOT TESTED** | Source review only: the ISO script targets Debian 13/trixie amd64 and requires root plus `live-build`; this host is Ubuntu 26.04 and `live-build`, `lb`, and `qemu-system-x86_64` are unavailable. No ISO build, VM/physical boot, offline boot, or reboot-persistence test was attempted. | Live USB acceptance remains outstanding. `docs/LINUX_LIVE_USB.md` asks to verify session/report JSON after reboot, but the Live launcher selects SQLite as canonical storage and normal SQLite writes do not update legacy JSON. The existing-mounted-partition path also does not remount to enforce `nodev,nosuid,noexec`. |
| Physical hardware validation | **NOT TESTED** | Live discovery returned 33 host inventory records; only the CPU metrics diagnostic was executed through the real API. No camera, audio, display, keyboard, USB, USB-C, HDMI/VGA, battery-health, Wi-Fi-connectivity, Bluetooth-pairing, or other functional hardware procedure was performed. | Hardware availability/inventory is not proof of operation. Do not count untested devices as passing. |

## Environment

- Ubuntu 26.04 LTS, Linux x86_64 (`Linux hswm-Latitude-3510 7.0.0-43-generic`).
- System and virtualenv Python: 3.14.4; system pip: 25.1.1; virtualenv pip: 26.3; virtualenv psutil: 7.2.2.
- Node.js: 22.23.4; npm: 10.9.9; Git: 2.53.0.
- `sqlite3`, `live-build`/`lb`, and `qemu-system-x86_64` commands were unavailable.
- Frontend browser command was Chromium from `/snap/bin/chromium` (also available as `/usr/bin/chromium-browser`).

## Exact validation commands and procedures

**Backend:** the exact command and isolation setup are recorded in the verification matrix. Test data was copied to a fresh temporary directory so the full suite did not use or overwrite operational data.

Environment probes used `uname -a`, `cat /etc/os-release`, `python3 --version`, `pip3 --version`, `node --version`, `npm --version`, and `git --version`; system/virtualenv pip were distinguished with `/usr/bin/python3 -m pip --version` and `./.venv/bin/python -m pip --version`.

**Frontend:** `cd frontend && npm run build`; then `cd frontend && npm run`. The latter showed no test script. A glob search for frontend `*.test.*` and `*.spec.*` files found none.

**Real API and restart:** an inline `./.venv/bin/python - <<'PY'` harness started Uvicorn twice as separate processes with a fresh temporary `DATA_DIR`, `STORAGE_BACKEND=sqlite`, and `SQLITE_DATABASE_PATH`. It called:

1. `GET /health/` and `GET /devices/`.
2. `POST /diagnostic-sessions/` with asset creation.
3. `PUT /diagnostic-sessions/{session_id}/intake`.
4. `POST /diagnostic-sessions/{session_id}/diagnostics/cpu/cpu`.
5. `PUT /diagnostic-sessions/{session_id}/technician-record` and `GET /diagnostic-sessions/{session_id}/report`.
6. Stopped the API process, started it again with the same temporary SQLite file, and repeated `GET /diagnostic-sessions/{session_id}` and `GET /diagnostic-sessions/{session_id}/report`.
7. Ran Python `sqlite3` `PRAGMA integrity_check`.

A second inline Python harness ran the real workflow API `POST /diagnostic-sessions/{session_id}/execute?device_id=cpu` with `{"diagnostics":["cpu","memory","storage","network"]}` and inspected the returned report statuses and summary.

**Migration:** the inline API harness copied `data/reports` to a temporary source directory, hashed its JSON files, and invoked `./.venv/bin/python -m app.persistence.local.import_legacy --sessions <temporary-empty-sessions> --reports <temporary-copy-of-data/reports>` twice with a temporary SQLite destination. The first run imported 13 reports; the second reported 13 skipped. Source hashes were unchanged.

**Normal launcher:** an isolated temporary working copy (with repository code and built UI symlinked into it, copied legacy report inputs, and fresh writable data/state directories) ran `bash scripts/run_uhdp_linux.sh --no-browser`. It verified API/UI health, Chromium root-page rendering, SQLite integrity/import count, and process shutdown. This did not run the installer or use the real `.env`.

The browser smoke used Chromium with `--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --user-data-dir=<temporary-profile> --virtual-time-budget=3000 --dump-dom http://127.0.0.1:3000/`.

**Live USB and filesystems:** only `command -v` availability checks and source/document review were performed. No disk, partition, USB filesystem, ISO writer, or boot device was formatted or modified.

**Other checks:** `git diff --check` passed. A path validation script extracted all 33 `.py` references in `docs/UHDP_UBUNTU_BLOCKER_RESOLUTION.md`; every referenced path exists after correcting the test paths to `tests/`.

## Frontend workflow inspection

Source inspection covered `frontend/src/routes/index.tsx`, `App.tsx`, the shared layout/sidebar/session context, all page components under `frontend/src/pages/` (Dashboard, DeviceDiscovery, SessionOverview, QcInspection, CosmeticInspection, Results, ReportViewer, QaReview, Photos, ActiveQc, QcHistory, Reports, StationSetup, and FieldRequirements), and the standalone display diagnostic page. API calls in those pages use the configured local backend client; the API client targets port 8000 on the UI host. The server-side API workflow above is real, but the browser was not driven through the full workflow.

Source-level concerns to resolve or explicitly accept:

- Device intake automatically uses the first discovered device with type `system`; there is no user device-selection control if multiple system devices are returned.
- New intake/asset selection and unsaved form edits are held in page state until the save/continue action. Leaving or refreshing before saving can lose those edits.
- Display tests can be submitted as skipped; the UI's completion gate checks that every required item has a latest result, not that every result passed. The backend evaluator correctly makes skipped/inconclusive display outcomes non-passing.
- Status badges explicitly style pass/fail/error/warning/unsupported and a few lifecycle states; `inconclusive`, `blocked`, `cancelled`, and `not_applicable` fall back to neutral styling and raw labels.
- QA “finalized” wording is derived from the saved technician disposition fields rather than an independently loaded session-finalized state.

These are source observations, not findings from a simulated browser interaction. Back navigation, API error recovery, and data retention after browser refresh remain unverified in a live interactive run.

## Diagnostic categories and status semantics

| Category | Observed implementation/evidence | Audit classification |
|---|---|---|
| CPU | Standard CPU diagnostic records processor, architecture, core counts, usage, and frequency. The evaluator accepts a positive physical-core count as PASS. The separate CPU-stress diagnostic runs bounded arithmetic but uses completion, not a health threshold, for PASS. | Standard path: inventory/metrics only; observed API PASS is not functional health evidence. Stress path: bounded workload exists but was not run in this audit. |
| Memory | Standard diagnostic records `psutil.virtual_memory()` capacity/use; evaluator accepts positive installed capacity as PASS. Separate bounded stress allocates memory and writes/readbacks pages, but does not turn nonzero mismatches or cancellation into a non-pass result. | Standard path: inventory/metrics only and currently can PASS. Stress path: code-level status defect; not run in this audit. |
| Storage | Standard diagnostic enumerates mounted partitions and calls `disk_usage`; evaluator accepts a nonempty volume list as PASS. No read/write health benchmark was run. | Inventory only; current PASS does not establish physical-drive health. |
| Network / Wi-Fi / Bluetooth | Network adapter inventory is explicitly inconclusive without `connectivity_verified`; Linux Wi-Fi and Bluetooth probes inventory interfaces/controllers but do not test connectivity or pairing. | Inventory only; network connectivity, Wi-Fi association, and Bluetooth pairing NOT TESTED. |
| Battery | Linux sysfs inventory reads battery presence and fields such as `capacity_percent`, energy and cycle data. The generic evaluator looks for `percent`; no battery functional-health run occurred. | Inventory/telemetry only; evaluator field mismatch can leave Linux battery results inconclusive. |
| Display / HDMI / VGA | Linux DRM connector inventory is not a panel or signal test. The separate display workflow records technician outcomes; all required outcomes must be recorded and any skip/inconclusive prevents evaluator PASS. | Inventory plus technician-assisted visual assessment; physical display/port validation NOT TESTED. |
| Webcam / keyboard / speaker / USB / USB-C | Linux paths inventory `/dev`, input, ALSA, sysfs, or Thunderbolt evidence and return inconclusive/not-applicable/unsupported rather than claiming operation. | Hardware inventory only; live image, key input, audible output, data transfer, and port function NOT TESTED. |
| System | Captures hostname, OS, architecture, processor and Python version, then sets raw status to PASS; it is not a hardware test. | System inventory only; must not be interpreted as diagnostic health PASS. |
| Technician/manual checks | API records technician decisions, notes, detected devices, and evidence. Display/cosmetic workflows also require manual observations. | Manual workflow is implemented and test-covered; no physical manual check was performed. |
| Permission / unsupported / infrastructure | Permission-denied inventory is represented as blocked/inconclusive by the API mapping and regression tests; unsupported and error states are distinct in backend enums/evaluation. | Software paths covered by tests. No physical permission-denied or infrastructure-failure scenario was deliberately induced. |

The real four-category workflow completed with `workflow_status=success` while its report summary showed three passes and one inconclusive. That result exposes a contract problem: the workflow-generated CPU/memory/storage records had no evaluator object, and the report summary counted their raw inventory status as PASS. The passing suite does not resolve this.

## Modified and inspected files

**Modified in this audit:** `docs/UHDP_UBUNTU_BLOCKER_RESOLUTION.md` (corrected verified test paths from `app/...` to `tests/...`); added `docs/UHDP_PHASE1_FINAL_ACCEPTANCE_AUDIT.md`.

**No production code or tests were changed in this audit.** Pre-existing uncommitted work was preserved; the branch remains `main`.

**Inspected:** backend bootstrap/configuration, diagnostic routes/services/evaluator/providers, SQLite and legacy importer, test configuration and persistence/API tests; frontend routes, pages, API client, state/layout/status components and package scripts; `scripts/install_linux.sh`, `scripts/run_uhdp_linux.sh`, Live build/runtime scripts and packaged files; `README.md`, `docs/RUNNING_THE_APPLICATION.md`, and `docs/LINUX_LIVE_USB.md`.

## Outstanding blockers and reproducibility

1. Define and enforce functional evidence before CPU, memory, storage, and system diagnostics can be reported as health PASS; the memory stress result must account for mismatches and cancellation.
2. Complete real browser-driven technician workflow testing, including device selection, refresh/back behavior, error recovery, review, and report routes.
3. Build the Live image on its supported Debian 13 amd64 build host, then boot-test online/offline and verify SQLite/session/report persistence across shutdown/reboot on the intended removable data partition without touching internal disks.
4. Perform physical hardware tests for every supported device category. Inventory evidence is not a substitute.
5. Align Live USB reboot-acceptance instructions with SQLite as canonical storage; verify session/report data in SQLite and any actual exported snapshots rather than expecting new legacy JSON files.

The backend suite and isolated API/launcher/migration procedures are reproducible when the same dependencies and free ports are available. Live USB and physical-hardware results are not reproducible from this Ubuntu host because the required build/boot environment and hardware procedures were unavailable.

**Overall verdict: NOT READY**
