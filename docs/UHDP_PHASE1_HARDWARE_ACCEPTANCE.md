# UHDP Phase 1 Hardware and Linux Acceptance

**Status as of 2026-11-06: NOT RUN**

No physical hardware diagnostic, stress test, Live USB boot, or browser-driven
technician flow was executed during the closure baseline. The current host is
Ubuntu 26.04 LTS, not the Debian 13-based Live environment.

| Acceptance area | Current evidence | Status | Required closure evidence |
|---|---|---|---|
| Linux installation and launcher | `scripts/run_uhdp_linux.sh` inspected; not launched | Not verified | Run as the technician account; verify startup, health checks, UI service, logs, shutdown, and relaunch |
| API and UI health | Backend tests and frontend build pass | Not verified end to end | Start the application and verify both loopback endpoints on Linux |
| Browser technician workflow | Chromium is installed; no browser test run | Not verified | Create a session, discover/select a device, run diagnostics, record manual checks and disposition, generate/view the report, and verify persisted state after restart |
| SQLite canonical persistence | Isolated backend suite passed; no live application restart test | Not verified end to end | Verify session, asset, diagnostic, report, and audit records through existing SQLite-backed paths across application restart |
| Report output | Existing report tests are included in the backend suite | Not verified on a technician run | Confirm JSON and HTML report content and session identity from the completed workflow |
| CPU and memory | No physical test run; current evaluators include inventory-only PASS paths | Not accepted | Correct result semantics first; then use bounded, cancellable tests with resource limits and temperature monitoring where available |
| Storage | No physical test run; no storage writes were performed | Not accepted | Validate inventory/result correctness without formatting, partitioning, erasing, or destructive writes |
| Network and battery | No physical test run; network connectivity is not tested and Linux battery field mapping is inconsistent | Not accepted | Verify only existing evidence paths; report missing hardware/sensors as not applicable or inconclusive rather than passed |
| GPU | No physical test run; no GPU diagnostic is registered in the default HAL registry | Not verified | Treat the existing optional GPU stress job separately; no new GPU diagnostic is included in this closure |
| Debian 13-based Live image | No image build or boot test; `live-build`, `lb`, and QEMU are absent | Not verified | Build with the documented Linux Live process and test boot, services, SQLite persistence, and restart on actual removable media |
| Live USB persistent data | `scripts/run_uhdp_live.sh` inspected; no USB was mounted or changed | Not verified | On identified removable media, verify persistent session/report/database data across Live reboot; avoid any unrelated disk changes |

The host has Chromium, `stress-ng`, `sensors`, and `lshw`, but their presence
does not establish that a diagnostic is integrated, safe, or passed. No
stress workload was started. This report does not authorize hardware writes,
stress testing, or installation of missing Live-image tooling.
