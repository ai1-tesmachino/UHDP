# UHDP Phase 1 Ubuntu Blocker Resolution

## Result

**PARTIALLY RESOLVED.** The reproduced backend suite now passes, and the diagnostic-to-SQLite workflow was exercised across an API process restart. This is not a Phase 1 acceptance decision: physical hardware behavior remains untested, and the frontend has no automated test runner.

## Environment and baseline

Validation ran on Ubuntu 26.04 LTS, Linux x86_64, Python 3.14.4, psutil 7.2.2, Node.js 22.23.4, npm 10.9.9, and Git 2.53.0. The Python virtual environment and frontend dependencies were used. The initial test environment lacked `httpx2` and `pytest-asyncio`; they were installed in the virtual environment only to run the suite. The `sqlite3` command-line utility is absent; database integrity was checked through Python's SQLite module. No dependency manifest or system package was changed.

The initial validation summary recorded **456 passed, 46 failed (502 total)**. An isolated run of the untouched `HEAD` archive on this host reproduced **458 passed, 44 failed (502 total)**. The two-failure discrepancy could not be resolved from the retained initial summary; the 44 failures reproduced from the archived commit are classified below. The final suite contains 13 additional tests and reports **515 passed, 0 failed, 45 warnings**.

## Failure classification and resolution

| Classification | Reproduced failures and root cause | Correction |
| --- | --- | --- |
| Ubuntu compatibility / shared upstream defect | 15 API, discovery, and session test failures reached `app/discovery/providers/network_provider.py` and raised `AttributeError: module 'psutil' has no attribute 'AF_INET'`. Affected tests: `tests/api/test_devices.py` (`test_get_devices`, `test_get_device`, `test_get_unknown_device`); `tests/api/test_diagnostic_session_execution.py::test_diagnostic_session_end_to_end`; `tests/api/test_diagnostic_session_routes.py` (`test_repeated_diagnostic_execution_and_retest_create_distinct_run_ids`, `test_execute_single_diagnostic`, `test_stress_duration_is_forwarded_through_session_api`, `test_technician_record_is_in_report_with_evidence_limited_health_scores`); all three `tests/discovery/test_discovery_service.py` cases; `tests/services/test_diagnostic_session_execution.py::test_diagnostic_session_executes_full_workflow`; both `tests/services/test_diagnostic_session_result_collection.py` cases; and `tests/services/test_diagnostic_session_service.py::test_execute_single_diagnostic`. | Use standard-library `socket.AF_INET` and `socket.AF_INET6`. Add IPv4/IPv6 provider regression coverage. |
| CPU engine selection | `tests/api/test_diagnostic_jobs.py::test_internal_cpu_job_runs_and_exposes_explicit_evaluation` expected the internal CPU engine although the installed `stress-ng` was selected. | Make the test isolate the internal-engine path by mocking `stress-ng` unavailable. Engine-selection metadata remains covered by the appropriate execution tests. |
| Linux inventory expectations | `tests/discovery/test_linux_inventory_providers.py::test_linux_storage_reads_physical_disk_identity_and_capacity`, `test_linux_display_reports_connected_modes`, and `tests/discovery/test_storage_provider.py::test_storage_discovery` asserted host-dependent identity/status/display values not guaranteed by Linux inventory. | Keep Linux discovery coverage and assert platform-appropriate availability and returned modes rather than assuming physical identity or a fixed display mode. |
| Diagnostic status/evaluation mismatches | `tests/hal/test_basic_hardware_diagnostics.py::test_usb_diagnostic_passes`, `test_usb_diagnostic_handles_error`, and `test_battery_diagnostic_handles_error` expected PASS/ERROR despite running Linux inventory paths; `tests/hal/test_usb_diagnostic.py::test_usb_diagnostic` expected PASS from inventory without functional evidence. | Explicitly mock Windows for the USB/battery tests covering the Windows command path. Keep Linux USB inventory inconclusive without sufficient evidence, and preserve PASS, FAIL, UNSUPPORTED, INCONCLUSIVE, PERMISSION DENIED, and INFRASTRUCTURE ERROR meanings. |
| Windows-specific assertions | The parametrized `test_basic_hardware_diagnostic_passes` cases (Display, Webcam, Keyboard, Speaker, USB-C, HDMI, VGA, Wi-Fi, Bluetooth), `test_basic_hardware_diagnostic_handles_error` cases (Display, Webcam, Keyboard, Speaker, USB-C, HDMI, VGA, Wi-Fi, Bluetooth), and `test_hdmi_diagnostic_queries_connection_parameters` / `test_vga_diagnostic_queries_connection_parameters` in `tests/hal/test_display_connector_diagnostics.py` exercised PowerShell command-result behavior while running on Linux. The latter two raised `AttributeError: 'NoneType' object has no attribute 'args'`. | Explicitly mock Windows in tests whose purpose is to cover Windows command paths, preserving meaningful PASS/ERROR assertions. |
| Invalid QA test request | `tests/api/test_diagnostic_session_routes.py::test_station_profile_retest_and_qa_disposition_persist_in_report` received HTTP 422 instead of 200 because the test sent stale QA input/identifiers. | Use valid current request fields and IDs; retain the API validation behavior. |
| SQLite/file-storage expectation | The initial validation identified report-action assertions that treated JSON files as the primary store, contrary to the configured SQLite backend. These particular failures did not recur in the archived-`HEAD` rerun. | Update report-action tests to inspect SQLite persistence while retaining JSON and HTML export coverage. |
| Network evidence contract | Network adapter inventory alone was previously treated by some tests as proof of connectivity. | Network inventory without explicit connectivity evidence is `INCONCLUSIVE`. The API, evaluator, session summary, report, and technician workflow now preserve that status. |

Two additional production defects were exposed while following the diagnostic path beyond the original `psutil` exception:

- `WorkflowResult` is not a dataclass and could not be serialized by the generic SQLite serializer. Session serialization now writes and restores its typed status/message representation.
- Permission-denied probe results were not consistently surfaced as blocked/inconclusive, and network adapter presence was not sufficient evidence for a connectivity PASS. These outcomes are now represented explicitly and remain non-passing.

## Data-directory and persistence changes

Unset session/report paths now derive from configured `DATA_DIR`; explicit environment and dotenv paths remain authoritative. The normal Linux launcher uses configured paths and imports repository legacy sources (`data/sessions`, `data/reports`, and `reports`) without modifying the JSON files. The Live launcher continues to keep its data under persistent `UHDP_DATA`. SQLite remains canonical, and migration is idempotent.

The migration exercise imported 13 legacy reports, imported none on the repeat run, left source JSON hashes unchanged, and returned SQLite `integrity_check` as `ok`. No existing database was overwritten.

## Files changed

**Production and launcher:** `app/discovery/providers/network_provider.py`, `app/hal/diagnostic_evaluator.py`, `app/hal/diagnostics/network_diagnostic.py`, `app/hal/diagnostics/platform_probes.py`, `app/hal/models/diagnostic_result_collection.py`, `app/persistence/local/import_legacy.py`, `app/persistence/session_serialization.py`, `app/services/diagnostic_session_service.py`, `app/core/config.py`, `scripts/run_uhdp_linux.sh`.

**Tests added or updated:** `tests/persistence/test_session_serialization.py` (new), `tests/test_config_paths.py` (new), `tests/api/test_diagnostic_jobs.py`, `tests/api/test_diagnostic_session_routes.py`, `tests/api/test_profile_execution_contract.py`, `tests/api/test_workflows.py`, `tests/discovery/test_linux_inventory_providers.py`, `tests/discovery/test_storage_provider.py`, `tests/hal/test_basic_hardware_diagnostics.py`, `tests/hal/test_diagnostic_evaluator.py`, `tests/hal/test_display_connector_diagnostics.py`, `tests/hal/test_network_diagnostic.py`, `tests/hal/test_platform_probes.py`, `tests/hal/test_usb_diagnostic.py`, `tests/integration/test_full_system_validation_execution.py`, `tests/persistence/test_identity_foundation.py`, `tests/scripts/test_linux_runtime_scripts.py`, `tests/services/test_diagnostic_session_execution.py`, `tests/workflow/integration/test_full_hardware_workflow.py`, `tests/workflow/test_save_report_action.py`, `tests/workflows/templates/test_full_system_validation_workflow.py`.

**Documentation:** `README.md`, `docs/RUNNING_THE_APPLICATION.md`, and this report.

## Validation performed

- Focused diagnostic/session regressions: **68 passed**; final status-contract expectation set: **13 passed**.
- Full backend suite, isolated from existing operational data: **515 passed, 0 failed, 45 warnings**. No tests were skipped in that run.
- Local reopen authorization and audit-event tests: **11 passed**.
- API-process restart scenario: created a session and asset, executed diagnostics, recorded technician review, generated/retrieved the report after restarting the API, and verified SQLite integrity.
- Legacy report migration: 13 imported initially, 0 duplicate imports on repeat; source JSON remained unchanged.
- Frontend production build: passed with Vite. `frontend/package.json` has no frontend test script or automated frontend test suite.
- Headless browser smoke against the production UI displayed the session's network result as `inconclusive`.
- `git diff --check`: passed.

## Remaining limitations

- Physical camera, audio, display, USB, network-connectivity, and other hardware behavior: **NOT TESTED**. Inventory and mocked/provider tests do not establish physical-device functionality.
- No automated frontend tests are configured; production build and browser smoke are not substitutes for a frontend test suite.
- The `sqlite3` CLI is unavailable; Python's SQLite module was used for integrity verification.
- The initial reported 46-failure set differed by two tests from the isolated archived-commit rerun (44 failures); those two could not be identified from the retained initial summary.

This report documents blocker resolution only. It does not claim Phase 1 acceptance or authorize Phase 2 work.
