# UHDP UI Consumer Feedback — Technician Walkthrough

**Commit tested:** `771969b` (`feature/phase2-diagnostics`, 6 commits ahead of `origin/main`, not pushed)
**Method:** real application driven in headless Chromium (CDP) against a live backend — station setup, intake, cosmetic inspection, functional check, QA disposition, report export, history, delete/reopen, theme, sidebar, mobile viewport
**Environment:** frontend `http://127.0.0.1:3002` (Vite), backend `http://127.0.0.1:8000` (`STORAGE_BACKEND=sqlite`, `DATA_DIR=/tmp/uhdp_ui_data`), Chromium 157 headless, viewports 1440×1000 and 390×844
**Not performed:** visual pixel review (screenshots captured but not visually interpretable by the tester), load testing, penetration testing, authenticated multi-user testing

> Perspective: this is written as a **consumer/technician using the product**, not as a code reviewer. Findings are graded for a local bench appliance that may also be reachable over a LAN.

---

## 1. Executive summary

The core inspection workflow is real and mostly works. I created a session, saved cosmetic and functional checks, finalized a QA disposition, opened a report from history, and exercised theme, sidebar, and the delete dialog with no console exceptions after the CORS configuration was corrected.

The two problems that would stop me trusting the product in a real shop:

1. **The app opens on demo data**, and the real QC workflow is not in the sidebar — a new user is shown fake ThinkPads and 24 fake reports, with no visible "start real work" path.
2. **Report status contradicts the disposition.** With 26 of 27 functional checks never run, the app suggested `READY FOR RESALE` and exported a report with `Status: passed` — in the same document that records the disposition `Inspection incomplete / retest required`.

Everything else below is friction, not architecture. No rewrite is implied.

| Dimension | Rating | Rationale |
|---|---|---|
| First-run / orientation | **D** | Lands on demo dashboard; real workflow hidden behind URLs |
| Report trustworthiness | **D** | Status ignores unperformed checks; contradicts disposition |
| Error communication | **D+** | Raw Axios strings shown to technicians |
| Intake usability | **C−** | 18,000 px raw inventory dump before the form |
| QA / disposition flow | **C** | Works, but no coverage guardrail; contradictory post-save UI |
| Core check flows | **B+** | Gating, autosave, progress counters behave correctly |
| Interaction polish | **B** | Theme, sidebar, dialog focus, validation all good |
| Mobile | **C** | Dashboard fine; history table 866 px wide at 390 px |

---

## 2. What I did

1. Set up station as `Consumer Tester / BAY-7`, then `Audit Technician / STATION-UI-TEST`.
2. Started real intake via `/devices?new=1`, chose **"Continue without asset identification"**, entered asset tag `SN-CONSUMER-001`, workflow **Service center**.
3. Confirmed intake → session `0dd173ce-2c13-4756-9b12-20b13ede3939`.
4. Cosmetic: one item confirmed (condition + severity + confirm checkbox).
5. Functional: one check set to **Pass** and saved ("1 Of 27 Saved").
6. QA: disposition **"Inspection incomplete / retest required"**, approver `Consumer Tester`, deviation reason entered.
7. Opened `/report`, `/reports`, and the exported HTML report; checked `/history`, delete dialog, reopen form.
8. Exercised theme toggle, sidebar collapse, invalid session IDs, and a 390×844 viewport.

---

## 3. P1 — Trust and entry point

### 3.1 The app opens on demo data, and the real workflow is not in the navigation

**Evidence**

- `/` renders `TechnicianDashboard` with hardcoded sample data: Lenovo ThinkPad T480, Intel Core i5-8350U, 16 GB, 256 GB, plus **24 fake reports**.
- The string **`DEMO MODE`** appears **3 times** on the first screen.
- The sidebar contains only **Dashboard / Reports / Settings**. Neither "Start New QC" nor "QC History" is reachable from it; real work lives at `/devices?new=1`, `/active-qc`, and per-session URLs.
- Completing station setup redirects to `/` — the demo dashboard.
- Every demo "View report" button only shows a toast: *"The demo report viewer is under development."*

**Impact:** a technician evaluating the product sees sample hardware, cannot find the real intake flow, and clicking the most prominent call-to-action produces an "under development" message. This is the single worst first impression in the app.

**Remediation**

- Land on real state (active session, or a real-device summary) and make demo data an explicit, dismissible mode.
- Add "Start New QC" and "QC History" to the primary sidebar.
- Remove or disable demo buttons that only toast; never ship "under development" affordances in a customer-facing build.

### 3.2 Report status contradicts the QA disposition

**Evidence**

- Coverage at finalization: **1 of 27** functional checks, **1 of 18** cosmetic items.
- QA screen **suggested disposition: `READY FOR RESALE`**; the `not run` counter showed **0**.
- Finalized disposition: **`Inspection incomplete / retest required`** (with reason recorded).
- `/report`, `/reports`, and `/reports/{id}/html` all report **`Status: passed`**.
- Exported HTML contains both, side by side:

  ```text
  <strong>Status:</strong> passed
  "final_disposition": "Inspection incomplete / retest required"
  ```

- Source: `app/workflows/reporting/report_builder.py` (`_calculate_status` considers only recorded results) and `app/services/diagnostic_session_service.py` (`_refresh_report`, `_session_result_status`).

**Impact:** directly dangerous for the business. A report can leave the shop saying `passed` for a machine that was essentially not inspected, and the suggested disposition actively pushes toward resale.

**Remediation**

- Compute status from **planned vs completed coverage**, not only recorded results; introduce `incomplete` / `not_run` outcomes.
- Never allow `passed` to coexist with an incomplete or non-pass disposition.
- Count unperformed checks in the `not run` bucket.
- Make the suggested disposition refuse "ready for resale" below a coverage threshold.

### 3.3 Raw Axios errors are shown to the technician

**Evidence**

- Reopen with a wrong credential displayed: **`Request failed with status code 503`**. The backend returned `{"detail":"Local supervisor authorization is not configured."}`.
- Invalid session ID rendered **`Request failed with status code 404`** as the page body.

**Remediation**

- Extract and display `error.response.data.detail` in `frontend/src/api/client.ts`.
- Map common states to actionable copy, e.g. "Supervisor credential is not configured on this station — ask your administrator."
- Keep a technical detail expander for support, but not as the primary message.

---

## 4. P2 — Core workflow friction

### 4.1 Intake is a 17,000-pixel raw inventory dump

**Evidence**

- `/devices?new=1` is **18,051 px** tall; the intake form begins at **~17,145 px**.
- Above the form: "*System inventory · 40 entries*", CPU instruction-set arrays (`["fpu","vme","de","pse","tsc","msr",...]`), sensor arrays, `null` values, snake_case keys, and pseudo-devices such as `/dev/loop0` and `/dev/loop2`.

**Remediation**

- Put the intake form at the top.
- Replace the dump with a summary card ("Intel i5-10210U · 16 GB · 512 GB NVMe") and a "Show raw inventory" disclosure.
- Filter pseudo-devices out of the human-facing list.

### 4.2 The device has three identities at once

**Evidence**

- Session header: **`Dell Inc. Latitude 3510`**.
- History and report: device **`system`**.
- Serial: **`Not recorded`**, despite entering asset tag `SN-CONSUMER-001`.
- Context bar label: "Asset identity unresolved".

**Remediation**

- Resolve one display name and use it everywhere (header, lists, report).
- Carry the asset tag/serial through to session and report, or state explicitly that the asset was intentionally left unresolved.

### 4.3 QA screen has no coverage guardrail and contradicts itself after save

**Evidence**

- "Save QA disposition" became enabled with 26 of 27 functional checks untouched; no warning or confirmation about coverage.
- After a successful save the editable form remained, alongside **both**:
  - "QC disposition saved and session finalized"
  - "Save the reviewed disposition before final report export."

**Remediation**

- Block save (or require an explicit documented override) when coverage is materially incomplete.
- After save, replace the form with a read-only disposition summary and a single primary "Open report" action.
- Do not render a "not saved" warning once the save has succeeded.

### 4.4 The exported "report" is a JSON dump, not a customer document

**Evidence**

- `/reports/{id}/html` is a **~66 KB** HTML file whose body is dominated by an escaped JSON blob inside `<pre>` (`"manual_checks": { "charger": { ...`).
- `/results` similarly renders raw device inventory JSON.

**Remediation**

- Produce a human-readable report: headline result, coverage, per-check table, disposition, approver, timestamps.
- Attach raw JSON as a separate download for support/audit, not as the report body.

### 4.5 Port/origin fragility reads as "the system is broken"

**Evidence**

- Vite auto-incremented from `:3000` to `:3002`; because `CORS_ORIGINS` defaults to `:3000` only, the navbar flipped to **"Local system offline"** and pages showed **"Network Error"**.
- The app only worked after restarting the backend with the correct origin.

**Remediation**

- Allow `localhost`/`127.0.0.1` on any port in development, or make Vite fail instead of silently changing ports.
- Make the API base URL configurable instead of hardcoded.
- Distinguish "backend unreachable" from "CORS/origin blocked" in the status indicator.

---

## 5. P3 — Polish

| Finding | Evidence | Suggested fix |
|---|---|---|
| History table on mobile | 866 px table inside a 390 px viewport (inside a scroll container, page itself does not overflow) | Stacked card layout below ~640 px |
| React controlled-input warning | `/results` logs `` `value` prop on `select` should not be null `` | Use `""`/`undefined` consistently for the null option |
| Undefined "pending" counter | Context bar shows "Offline mode · 5 pending · 0 needs attention" with one session | Label the counter ("5 items queued for sync") |
| Demo-only affordances | "View report" toasts "under development" | Remove from non-demo builds |
| "Created" vs completed state | API session status showed `created` while the UI stepper showed Intake done and checks saved; `report_status` null on the session object while `/reports` says `passed` | Align session status, stepper, and report status |

---

## 6. What worked well

- **Station setup validation:** empty submit blocked by native validation with per-field messages; valid submit persists and redirects.
- **Cosmetic gating:** confirm checkbox stayed disabled until condition and severity were chosen; progress updated to "A Top lid 1 / 4 checked".
- **Functional flow:** Pass selectable, Save enabled only after choosing a result, counter updated to "1 Of 27 Saved".
- **Theme:** toggle flips `light → dark`, persists in `localStorage`, updates label ("Switch to dark theme" / "Switch to light theme") and colors.
- **Sidebar collapse:** 247 px → 67 px, label flips to "Expand sidebar".
- **Delete confirmation:** `role="alertdialog"`, initial focus on **Cancel**, dismisses cleanly.
- **Accessibility basics:** skip link present, no unlabeled interactive controls, no images missing `alt`, no horizontal page overflow at 1440 or 390.
- **Stability:** zero console errors and zero unhandled exceptions across all tested routes after CORS was correct.

---

## 7. Suggested sequence if this were my backlog

1. **Stop shipping false `passed` reports** — coverage-aware status and disposition guardrail (P1 3.2, P2 4.3).
2. **Fix the front door** — real landing page, real nav entries, remove demo stubs (P1 3.1).
3. **Human-readable errors** — central detail extraction (P1 3.3).
4. **Make intake usable** — form first, inventory collapsed (P2 4.1).
5. **One device identity** — name, asset tag, serial consistency (P2 4.2).
6. **Presentable report export** — HTML summary, JSON as attachment (P2 4.4).
7. **Dev-environment hardening** — CORS/port behavior, configurable API base (P2 4.5).
8. **P3 polish** — mobile table, null select, counter labels.

---

## 8. Test artifacts and state

- Sessions created during testing live in `/tmp/uhdp_ui_data` (SQLite), not in the repository.
- No application code was modified.
- CDP harness: `/tmp/uhdp_audit.mjs` (supports `VP_WIDTH`/`VP_HEIGHT`), `/tmp/uhdp_cdp.mjs`.
- Raw per-page captures: `/tmp/audit*.json`, `/tmp/audit*.png`.
- Running processes at time of writing: uvicorn on `:8000`, Vite on `:3002`, Chromium CDP on `:9222`. Ports `:3000`/`:3001` belonged to unrelated node processes and were left untouched.
