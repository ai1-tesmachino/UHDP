# UHDP Phase 1 Closure Baseline

- **Inspection date:** 2026-11-06
- **Checkout:** `main`, `30d66480eac01d0d7bbef5f671da0348853b7684`
**Baseline status:** backend tests and frontend production build pass; Phase 1 acceptance is not yet established.

## Repository state

The checkout contains uncommitted Phase 2 runtime work. There are 21 modified
tracked files and 8 untracked Phase 2 files; none are staged. The full inventory
and preservation boundary are recorded in
[`UHDP_PHASE2_EXISTING_WORK_PRESERVATION.md`](UHDP_PHASE2_EXISTING_WORK_PRESERVATION.md).
The tracked diff is 937 insertions and 280 deletions. No Phase 1 source files
were modified during this baseline inspection.

Recent commits:

```text
30d6648 fix: resolve Ubuntu Phase 1 blockers
25d9848 fix: avoid Ubuntu Node.js npm package conflict
d41a4c3 fix: complete Phase 1 Linux runtime corrections
8767f9c feat: complete Phase 1 identity and QC foundation
70e9698 feat: add technician QC workflow and UI foundation
```

## Environment and validation

The current host is Ubuntu 26.04 LTS on Linux x86_64 (kernel
`7.0.0-43-generic`), with Python 3.14.4, pytest 9.1.1, Node.js 22.23.4, and
npm 10.9.9. Chromium, `stress-ng`, `sensors`, and `lshw` are available.
`live-build`, `lb`, and `qemu-system-x86_64` are not available.

| Check | Command | Result |
|---|---|---|
| Backend suite | `DATA_DIR=/tmp/uhdp-phase1-baseline.oyYM8W/data pytest -q -c app/pytest.ini tests --tb=short` | **529 passed, 0 failed, 45 warnings** in 26.93s |
| Frontend production build | `npm --prefix frontend run build` | **Passed**, Vite 7.3.7; 2,286 modules transformed |

The backend test data directory was isolated from application data and removed
after the run. The current backend count includes the uncommitted Phase 2 tests;
it therefore describes this checkout, not only the latest commit. The tests
and build do not establish physical-device, actual-browser-workflow, Linux Live
USB, or application-restart acceptance.

Older audit and blocker documents contain results from different commits,
hosts, and test selections. Those historical checkpoints are retained as
historical evidence; the results above are the current checkout baseline.

## Verified implementation observations

- `DiagnosticEvaluator` can report CPU, memory, or storage as passed based
  respectively on a positive physical-core count, installed RAM capacity, or
  a non-empty list of reported drives. Those observations alone do not prove
  component health.
- Linux battery inventory reports charge as
  `batteries[].capacity_percent`; the evaluator looks for top-level `percent`.
  The Linux diagnostic can return raw `PASSED` while evaluated battery health
  remains inconclusive.
- Network diagnostics report adapter inventory and explicitly do not verify
  connectivity. The evaluator correctly leaves that result inconclusive.
- The system diagnostic returns raw `PASSED` after collecting host metadata;
  the evaluator has no system-health rule.
- The direct diagnostics API returns raw HAL results. Session single-diagnostic
  and profile paths evaluate results, but the session workflow collector stores
  raw results without assigning an evaluation. Identical checks can therefore
  produce differently qualified outcomes depending on the execution path.
- The default HAL registry includes CPU and memory stress diagnostics, each
  duration-clamped to 1–30 seconds. The direct CPU stress diagnostic has no
  cancellation input; direct memory stress can break on cancellation or detect
  pattern mismatches and still return raw `PASSED`. The separate job service
  provides cancellation and applies mismatch evaluation, but this does not
  normalize the direct path.
- The default HAL registry contains no GPU diagnostic. A separate GPU stress
  job path exists; it is not evidence of a general GPU health diagnostic.
- `DiagnosticJobService` persists job snapshots as JSON under
  `DATA_DIR/diagnostic_jobs`; confirm that this operational job state is
  intentionally outside the SQLite canonical domain before changing it.

The source observations above are inspection findings, not new runtime or
hardware test results.
