# UHDP Technician-First UX Audit and Design Specification

- **Audit date:** 2026-11-07
- **Checkout at audit start:** `main`, `cbbb4b6` (`feat: complete Phase 1 runtime and diagnostics workflow`)
- **Scope:** Read-only audit and proposed design. No application, API, schema, dependency, or routing changes are included.

## A. Executive findings

UHDP already persists useful inspection information and has a substantial technician-facing workflow, but that workflow is spread across too many overlapping destinations. The default route is an editable hardware inventory, not a task-oriented dashboard. The sidebar exposes ten actions under four technical groupings, while `/sessions`, `/active-qc`, and `/history` all lead to overlapping inspection records, and `/results`, `/qa`, `/reports`, and `/report` divide review and reporting.

The largest operational gap is that the technician path does not run the backend's automated diagnostic workflow. The functional page saves technician-entered manual results and links to a dedicated display test. The backend has separate automated execution routes, but the inspected frontend API module and workflow do not call them. `/diagnostics` redirects to a standalone manual inspection rather than an automated diagnostic selector.

The most consequential correctness gap is the lack of one backend-owned inspection summary and completion policy. `WorkflowSteps` infers step completion in React using conditions such as “any manual result exists” or “any evidence exists.” QA separately computes a suggested disposition in React. The backend's finalizer verifies that a report and one of five allowed disposition strings exist, then marks the session `completed`; it does not enforce the displayed approval, completeness, or disposition eligibility rules. Thus a finalized lifecycle state is not an approval result, and client-side requirements are not a security or business-rule boundary.

Other verified problems:

- The session-list response omits `device_inventory` and `technician_record`, although pages treat list rows as full `DiagnosticSession` objects. Device/serial columns can fall back to IDs or “Not recorded,” and repair/resale filters inspect missing data.
- The reports list is assembled from all sessions, including sessions for which no report exists; opening one can produce a 404.
- Cosmetical-condition records and manual-check records coexist for overlapping physical items. The current route shows the dedicated detailed cosmetic assessment, but manual cosmetic checks remain accepted and contribute separately to reports.
- Evidence is stored against a session and optional diagnostic run. A cosmetic item stores evidence IDs in its record, but the upload request itself has no item/check association. Evidence operations require SQLite; supported Linux launchers select SQLite, while the Python settings default remains file storage.
- Asset selection is based on existing asset IDs, creating a new asset, or remaining unresolved. The intake's asset-tag/serial field is not an asset search or a device-resolution operation.

**Highest priority:** first make a persisted inspection plan, summary, progress, next action, and disposition eligibility authoritative in the backend; then make all screens render that same state. Separately, wire the technician workspace to actual automated diagnostics or clearly distinguish the manual-only workflow from automated execution.

## B. Current frontend inventory

Routes below are from `frontend/src/routes/index.tsx:25-73`; the sidebar actions are in `frontend/src/components/Sidebar.tsx:97-150`. `App.tsx` wraps the application in `StationGate`, `SessionProvider`, and the shared layout (`frontend/src/App.tsx:13-42`). The app shell also displays a current-session context bar and a seven-step navigation strip (`frontend/src/components/Layout.tsx:25-122`, `frontend/src/components/WorkflowSteps.tsx:8-17`).

| Page / route | Technician task, displayed information, actions and inputs | Backend / persistence / navigation | Confusion, duplication and recommendation |
|---|---|---|---|
| **Dashboard** `/` — `frontend/src/pages/Dashboard.tsx:170,312-324` | Inspect detected machine inventory; edit detected specifications, mark them verified, add a missing field/component, refresh and save. No active-work queue is the primary content. | `GET /devices/`, `GET /devices/inventory`, `PUT /devices/inventory`; merged data and corrections persist as station inventory. “Continue to QC intake” goes to `/devices?new=1`. | This is an inventory maintenance screen presented as the home page. Rename/relocate the inventory editor to device/station tools; make `/` answer “what should I work on?” and provide start/resume/awaiting-completion actions. |
| **Station Setup** `/setup` — `frontend/src/pages/StationSetup.tsx:7,22-39` | Enter technician and station ID. These identify a workstation; the page explicitly says they are not authenticated sign-in. | Saves only `uhdp.station-profile` in browser `localStorage`; no backend operation. `StationGate` redirects here when the profile is absent. Returns to the interrupted route or `/`. | Keep under Settings after initial setup; distinguish station attribution from authenticated identity. Define behavior if local browser storage is cleared or multiple technicians share a workstation. |
| **QC Field Requirements** `/settings/field-requirements` — `frontend/src/pages/FieldRequirements.tsx:1,51-83` | Read a static list of mandatory/optional station, intake, cosmetic, and final-disposition fields; link to Station Setup. | Hard-coded `FIELD_GROUPS`; no API or persistence. | It is informational, not a configurable form or source of backend validation. Its statement that approver, attestation, and deviation reason are required exceeds backend enforcement. Keep as supervisor help only if the requirements are made authoritative. |
| **Device Intake** `/devices` — `frontend/src/pages/DeviceDiscovery.tsx:82,130-137,230-292,301,447` | Refresh discovery; view all reported properties and storage entries; select the system device; resolve asset by existing ID/new/unresolved; enter asset tag/serial, technician, work order, and workflow type; confirm intake. | `GET /devices/`, `GET /devices/inventory`, `GET /diagnostic-sessions/`; `POST /diagnostic-sessions/` followed by `PUT /diagnostic-sessions/{id}/intake`. Draft fields are in `localStorage`; confirmed intake and device inventory are persisted with the session. Continues to initial cosmetic assessment. | Device selection correctly requires explicit choice when there are multiple system candidates and preselects only a sole candidate. The page exposes raw inventory details before the task-critical identity fields. “Asset tag / serial / barcode” is free text and no barcode scanner or asset lookup is implemented. Make this the first step of a guided Start Inspection flow; show a concise identity confirmation and move raw details behind disclosure. |
| **Inspection workspace — initial cosmetic** `/qc?stage=cosmetic` — routed to `CosmeticInspection` by `InspectionRoute` (`frontend/src/routes/index.tsx:25-29,48`) | Record condition, severity, damage description/location, notes, confirmation, and optional item photos for a hard-coded list of physical items; add custom items; compare by area; mark all inspected. | `GET /diagnostic-sessions/{id}`; `PUT /diagnostic-sessions/{id}/cosmetic-inspection/initial`; photo upload via `/evidence/{session_id}`. Cosmetic state is embedded in the session payload; evidence IDs are stored on cosmetic items. Continues to functional checks. | Detailed assessment has 18 base items and a separate initial/final phase. Keep the assessment, but make it a stage inside one inspection workspace and confirm the required item set/product rules with operations. |
| **Inspection workspace — functional/manual** `/qc?stage=functional` — `QcInspection` (`frontend/src/pages/QcInspection.tsx:97,188,244-268,289-319`) | Load the manual checklist, enter Pass/Fail/N/A/Unable to verify and notes, save each item, then continue. It separately links to Display Diagnostics. | `GET /diagnostic-sessions/manual-checks`, `GET /diagnostic-sessions/{id}`, `POST /diagnostic-sessions/{id}/manual/{check_id}`, and `POST /diagnostic-sessions/{id}/complete`. Manual results and normalized test-result records are stored in the session/report. | This is a technician-assisted checklist, not the backend automated workflow. It hides some catalog checks, offers no manual “warning” or “not run” choice, and the UI-only “all saved” gate has no matching completion-policy endpoint. Unify manual and automated items in the workspace while preserving their different instructions and result semantics. |
| **Display diagnostic** `/diagnostics/display/:sessionId` — `frontend/src/diagnostics/display/DisplayDiagnosticPage.tsx:150-390` | Run full-screen display patterns; record test attempts, results, defect type/location/count, notes, and resume position; complete the display diagnostic. | Start/read/update/result/complete display endpoints under `/diagnostic-sessions/{id}/display/...`; updates are persisted in the session. Entered from the functional page (`QcInspection.tsx:301-319`). | Specialized interaction is justified, but it is a separate route without the global shell (`Layout.tsx:76-80`). Keep it as a focused workspace mode with an obvious return path and shared inspection context, not a separate navigation concept. |
| **`/diagnostics` redirect** — `frontend/src/routes/index.tsx:53` | Redirects to `/qc?stage=functional&standalone=1`. | No diagnostic catalog or execution call is made by this route. | The name implies automated diagnostic selection, but the destination is standalone manual inspection. Remove this ambiguity through a clear redirect/label or route to the actual automated test stage after that stage is wired. |
| **Session Overview** `/sessions` — `frontend/src/pages/SessionOverview.tsx:14,23-48,60-115` | View total/in-progress/completed counts, one “Active QC” item, and up to eight recent sessions; resume or open report. | `GET /diagnostic-sessions/`; activation then `GET /diagnostic-sessions/{id}`. Links to `/history`. | Duplicates Active QC and QC History. The list response lacks device inventory and technician record used by display helpers. Fold active/resume and recent items into Inspections; avoid a separate primary destination. |
| **Active QC** `/active-qc` — `frontend/src/pages/ActiveQc.tsx:15,24-75` | View the browser's active session identity, technician and lifecycle; resume or open the report. | Reads `SessionContext`, which keeps one active session ID in `localStorage` and loads the session API. Links to `/history`. | Duplicates the current-session card in `/sessions` and the resume actions in History/sidebar. Make resume an action on the Inspections list and persistent header. |
| **QC History** `/history` — `frontend/src/pages/QcHistory.tsx:25,44-84,106-126,140-178,193-225` | Search by session ID/device/serial; filter by completed/incomplete/repair/resale; resume, open report, reopen for retest, or delete. Reopen asks for actor label and local supervisor credential. | `GET /diagnostic-sessions/`, `GET /diagnostic-sessions/{id}`, `POST /{id}/reopen`, `DELETE /{id}`. Reopening retains the same session and starts a new report revision path; SQLite records an audit event. | Overlaps `/sessions` and `/reports`. Some filters cannot work on list payloads; there is no date, model, asset-tag, or completeness filter. Delete is prominent beside routine actions. Consolidate with Reports as History & Reports; keep reopen/delete behind clearly distinct permission/confirmation handling. |
| **Photos and Evidence** `/photos` — `frontend/src/pages/Photos.tsx:7,22-43,53-90` | Select a photo/log/file, explicitly confirm relevance, upload, view and download session evidence; continue to Results or QA. | `POST /evidence/{session_id}`, `GET /evidence/session/{session_id}`, `GET /evidence/{evidence_id}`. Files and metadata are persisted by `EvidenceStorage`/SQLite; frontend checks 100 MiB. | A separate stop in the workflow for evidence that often belongs to a specific defect. Embed capture in the relevant inspection item; retain a general device-photo section. No delete operation is exposed. |
| **Results** `/results` — `frontend/src/pages/Results.tsx:147,220-271,282-310` | Review report metadata, inventory, cosmetics, display, evidence, status counts, retest details and technician service notes; save technician record; continue to QA. | `GET /reports/{session_id}/json`, `GET /evidence/session/{id}`, `PUT /diagnostic-sessions/{id}/technician-record`; report is read from the configured report repository. | Very broad technical report-review page and overlaps QA and Report Viewer. Contains another editable technician-record form. Merge its decision-relevant summary into Review & Disposition; keep raw diagnostics in progressive disclosure/report. |
| **QA Review / Disposition** `/qa` — `frontend/src/pages/QaReview.tsx:24,52-97,107-153,163-200` | Review counts, choose a disposition, enter approver/reason, attest, optionally complete final cosmetic verification, save and finalize. | `GET /reports/{id}/json`, `PUT /diagnostic-sessions/{id}/technician-record`, then `POST /diagnostic-sessions/{id}/finalize`; final-cosmetic route returns to QA. | This is the actual disposition step, but its recommendation and final-cosmetic gate are client calculations. Backend does not enforce all of these rules. Make this one backend-driven review/decision stage, not a distinct technical QA module. |
| **QC Reports list** `/reports` — `frontend/src/pages/Reports.tsx:10,18-51` | Browse reports sorted by date and preview one. | `GET /reports/`; opens `/report?sessionId=...`. | Duplicates History and uses `device_id`, not readable model/serial. Backend may list sessions without reports. Fold into History & Reports. |
| **Report Viewer** `/report` — `frontend/src/pages/ReportViewer.tsx:56,81-125,151-194` | Read session report and outcome, view inventory/cosmetics/display/evidence/decision, download JSON, print, or open server HTML. | `GET /reports/{id}/json`, `/reports/{id}/html`, `/reports/{id}/revisions` (revision API exists but is not used by this page), and report sync status. Report content comes from report storage/revisions. | Keep as a report-detail view, not a separate navigation item. Prominently distinguish finalization/lifecycle from inspection outcome and identify report revision/finalization state. |
| **Not found** `*` — `frontend/src/routes/index.tsx:71-73` | Explains invalid route and returns to dashboard. | Client-only. | Keep, with a direct route back to active work if an inspection can be resumed. |

### Major shared components and state

- `frontend/src/components/Sidebar.tsx` — ten technician/admin actions, dynamic Active QC and Functional Inspection destinations, local health/sync indicators.
- `frontend/src/components/Layout.tsx`, `Navbar.tsx`, and `PageContainer.tsx` — global shell, active-session banner, current route and theme/sidebar controls.
- `frontend/src/components/WorkflowSteps.tsx` — seven client-rendered steps and locally inferred completion.
- `frontend/src/session/SessionContext.tsx` and `session/workflow.ts` — browser-level active/pending IDs, session refresh/polling, route-resume memory, device/serial display helpers.
- `AssetResolutionPicker.tsx`, `DeviceIdentityHeader.tsx`, `DeviceInformationCard.tsx`, and `SaveIndicator.tsx` — reusable intake/identity/save-state UI.
- `DiagnosticStatusBadge.tsx`, `DiagnosticProgress.tsx`, `DiagnosticCards.tsx`, `TestResultsList.tsx`, and `DiagnosticValues.tsx` — result presentation.
- `CosmeticAssessmentSummary.tsx` and `TechnicianAssessmentForm.tsx` — shared condition/review UI; inspect their usage before redesign so a new workspace does not duplicate existing behavior.
- `frontend/src/diagnostics/display/*` — dedicated display patterns, test catalog, result summary, and canvas.
- `frontend/src/components/ui/*` — existing UI primitives; no new component library is proposed.

## C. Current technician journey

```text
Launch browser
  -> StationGate checks browser-local technician/station profile
       -> missing profile: /setup -> save localStorage -> return to route or /
  -> / (Hardware Inventory, not task dashboard)
       -> discover host devices + load saved station inventory
       -> optional manual corrections/verification -> PUT station inventory
       -> Continue to QC intake
  -> /devices?new=1
       -> GET device discovery + station inventory
       -> choose system device (sole candidate may be preselected)
       -> choose existing asset ID / create asset / remain unresolved
       -> enter asset tag/serial, technician, work order, workflow
       -> POST session (client-generated/pending session ID)
       -> PUT intake and discovered inventory
  -> /qc?stage=cosmetic
       -> assess initial cosmetic items, save item data and optional photo IDs
  -> /qc?stage=functional
       -> save manual check results
       -> optional separate display-pattern workspace
       -> POST /complete
  -> /photos
       -> optional session-level evidence upload
  -> /results
       -> fetch JSON report, review summary and technician notes
       -> save technician service record
  -> /qa
       -> React derives suggested disposition
       -> optional final cosmetic verification
       -> save disposition record, then POST /finalize
  -> /report
       -> fetch report JSON, download JSON, print or open HTML
  -> /sessions, /active-qc, /history, /reports
       -> resume/open the same session or report from secondary entry points
```

### Navigation friction

1. The technician starts at inventory, then must recognize “Device Intake” as the inspection entry point.
2. The same saved work appears in QC Sessions, Active QC, QC History, and sometimes QC Reports.
3. The workflow step bar and the sidebar are parallel navigation systems; some steps are locked based on the current URL, not server eligibility.
4. Photos is a mandatory-looking separate workflow stop even though evidence can be attached directly to cosmetic items.
5. Results, QA, Reports, and Report Viewer each present some version of report/status information.
6. Display testing leaves the global shell; other test execution is not reached through the technician journey.
7. Resume routing is partly browser-local: `getQcResumePath()` prefers a saved URL; otherwise it returns intake or report (`frontend/src/session/workflow.ts:6-52`).

## D. Backend workflow map

The actual app mounts the combined devices/session/workflow/health router in `app/main.py:89-125` and the report, evidence, sync, runtime and other routers separately. The technician session endpoints are in `app/api/sessions/diagnostic_routes.py`; the service orchestrator is `app/services/diagnostic_session_service.py`.

| Technician operation | API and request/response | Service, validation, errors and state | Persistence |
|---|---|---|---|
| Discover system/device inventory | `GET /devices/` returns discovery objects (`device_id`, type, name, properties); `GET /devices/{device_id}` re-discovers and returns one or 404. | `discovery_service.discover()`; this is current host discovery, not asset resolution. | Live discovery; no inspection session write. |
| Review/correct station inventory | `GET /devices/inventory`; `PUT /devices/inventory` accepts `fields`, `notes`, `custom_components`; limits fields/notes and note length. | `app/api/devices.py:42-63`; stores under `local_station`. | `SQLiteDatabase` station_inventory payload. |
| Create or retrieve inspection | `POST /diagnostic-sessions/` accepts optional session UUID/device, asset ID or `create_asset`, asset tag, technician, station, customer reference, profile, retest source, planned diagnostic/manual arrays and workflow type. Returns session ID, lifecycle status, timestamp, asset ID and discovered devices. `GET /diagnostic-sessions/{id}` returns the full session snapshot. | `create_session()` is idempotent for a supplied existing session ID if asset resolution matches; rejects invalid or conflicting asset/retest identity. `get_session()` returns 404 if missing. Route schemas: `diagnostic_routes.py:116-170,175-202,622-659`; service: `diagnostic_session_service.py:78-284,738-759`. | `create_session_repository()` selects SQLite, Supabase or file backend. SQLite stores serialized session payload plus revisions, QC identity, component/run links and audit/outbox records. |
| List/resume/history | `GET /diagnostic-sessions/` returns only `session_id`, `status`, `created_at`, `device_id`, `asset_id`, and `intake_record`; delete is `DELETE /{id}`. | List is from `diagnostic_session_service.list_sessions()`; delete returns 404 if absent. The list schema is materially narrower than `GET /{id}`. | Soft delete in SQLite, file removal for file repository. |
| Save intake | `PUT /{id}/intake` body: `device_id`, `intake_record`, `device_inventory` (up to 300). Response confirms session/status/device/asset/intake. | Rejects missing/finalized session; replaces these intake fields and refreshes report. | Session repository, which serializes into SQLite when selected or JSON file in file mode. |
| Get checklist and save manual result | `GET /manual-checks` returns catalog entries (`id`, name, instructions). `POST /{id}/manual/{check_id}` accepts outcome, notes, scan status, detected devices, technician decision and evidence. | Service validates check ID, outcome and scan/decision consistency. Allowed result statuses include passed, failed, warning, not_applicable, blocked, not_run. Returns manual and normalized test-result records. | Embedded `manual_results`/`test_results` in session; report refreshed. |
| Run one automated diagnostic | `POST /{id}/diagnostics/{device_id}/{diagnostic_type}` accepts optional parameters/component ID and returns evaluated and raw status, execution status, result details and summary. | Service rediscovers device, validates session/device/component, executes `DiagnosticService`, evaluates result, stores run/test result, sets lifecycle `running`; route maps validation errors to 400/404. | Session payload and, in SQLite mode, normalized diagnostic run/result and identity records. |
| Run automated workflow | `POST /{id}/execute?device_id=...`, optional JSON `{ "diagnostics": [...] }`; absent/empty list defaults to cpu, memory, storage, network. Response includes workflow result, report identity/status/data and diagnostic summary. | Creates `full_system_validation_workflow`, executes, collects diagnostics; lifecycle can move running → checks_complete/failed → incomplete. Planned diagnostic/manual arrays are examined in `_session_result_status()` when present. Routes/service: `diagnostic_routes.py:688-809`, `diagnostic_session_service.py:1532-1684`. | Session, standardized results and report are persisted through configured repositories. |
| Display inspection | `POST /{id}/display/start`, `GET /{id}/display`, `PUT /{id}/display/progress`, `POST /tests/{test_id}/start`, `POST /tests/{test_id}/result`, `POST /display/complete`. | Pydantic restricts test outcome to passed/failed/inconclusive/skipped and validates defect types/counts. Service maintains attempts and prevents edits to finalized sessions; completion summarizes display outcomes. | Display diagnostic object embedded in session; report refresh on writes. |
| Cosmetic inspection | `PUT /{id}/cosmetic-inspection/{initial|final}` with `{items: {...}}`, max 40 items. Each item has condition, severity, damage fields, evidence IDs, confirmation/custom/model-dependent flags and areas. | Route validates shape/literals; service stores phase record and rejects finalized session writes. There is no backend required-item catalog or completion validator in this route. | `cosmetic_inspections` embedded in session and included in report data. |
| Complete checks | `POST /{id}/complete`; response only session ID/status. | Rebuilds report then sets lifecycle to `incomplete` when report is absent/incomplete/pending, otherwise `checks_complete`. This does not mean tests passed. | Session repository. |
| Save technician record / finalize | `PUT /{id}/technician-record`; optional record fields include disposition enum, reason, approver, service notes and grade. `POST /{id}/finalize` returns ID/status. | Service persists submitted fields and refreshes report. Finalizer requires report plus one allowed disposition, finalizes latest report revision, sets `status="completed"`. It does not itself enforce the frontend's attestation, approver, deviation-reason, cosmetic, or completeness conditions (`diagnostic_session_service.py:874-909,1402-1423`). | Session and report repositories; SQLite report revisions have finalize-once/immutability triggers. |
| Reopen for retest | `POST /{id}/reopen` body has actor label and secret credential. | Restricts to local requests; checks configured supervisor credential/rate limit; writes audit events; clears disposition/approval fields and sets same session back to `checks_complete`. Reports track superseded revisions. | Session, report revision, and audit event. |
| Upload/list/download evidence | `POST /evidence/{session_id}` streams raw bytes; requires `X-UHDP-Confirmed: true`, supported media type and configured size limit; optional `run_id`. `GET /evidence/session/{id}`; `GET /evidence/{evidence_id}`. | `_require_sqlite()` returns 409 unless `STORAGE_BACKEND=sqlite`; storage validates session/run ownership and integrity. Upload refreshes the report. | File in configured evidence storage; metadata, SHA-256, session/run association and audit/outbox in SQLite. |
| List/retrieve reports | `GET /reports/`, `GET /reports/{session_id}`, `/json`, `/html`, `/revisions`. Frontend's `getReport()` uses `/reports/{id}/json`. | List iterates all sessions and falls back to lifecycle status if report status/file is absent; JSON retrieval requires both session and report. This can list a session with no retrievable report. | Configured report repository; SQLite stores report JSON/HTML and immutable revisions, and also writes report revision files. |

### Persistence facts

- `Settings.STORAGE_BACKEND` defaults to `"file"` (`app/core/config.py:25-31`); `.env.example` selects SQLite, `README.md:60-67` describes SQLite, and both supported Linux launchers select SQLite (`scripts/run_uhdp_linux.sh:156-182`, `scripts/run_uhdp_live.sh:90-97`). A direct launch without `.env` or launcher therefore differs from the supported Linux path.
- SQLite schema stores the session payload/revisions, reports/revisions, diagnostic runs/results, evidence, audit events, assets, hardware components and session-asset links (`app/persistence/local/migrations/0001_local_records.sql`, `0002_domain_evidence.sql`, `0006_asset_component_identity.sql`). The payload remains the complete session snapshot; normalized tables provide identity, run, evidence and revision constraints.
- Intake draft and station profile are browser-local; station inventory, session/report state, manual/display/cosmetic records and report revisions use backend persistence. Evidence content is separately stored and only available in SQLite mode.
- `final_disposition` lives in `technician_record`; it is not the same field as `session.status` or `report.status`.

## E. Frontend/backend mismatch report

Severity reflects risk to technician action or decision correctness, not code quality.

| Severity | Verified mismatch | Evidence and impact |
|---|---|---|
| **Critical** | **Technician workflow does not invoke automated diagnostic execution.** | The backend exposes session `/{id}/execute` and individual diagnostic routes (`app/api/sessions/diagnostic_routes.py:249-331,688-809`), but `frontend/src/api/execution.ts:109-279` contains session/manual/display/complete calls and no automated-execution wrapper. `QcInspection.tsx:188-268` saves manual results and completes the session; `/diagnostics` redirects to standalone manual inspection (`routes/index.tsx:48-53`). A technician following the main flow cannot run the general CPU/memory/storage/network workflow from the UI. |
| **Critical** | **Disposition eligibility is enforced in React, not by the backend.** | `QaReview.recommendation()` computes its own outcome and `saveDisposition()` requires attestation/approver/reason in the browser (`frontend/src/pages/QaReview.tsx:24-59,143-172,250-268`). `finalize_session()` checks only report existence and membership in the disposition allow-list before finalizing (`app/services/diagnostic_session_service.py:874-909`). A direct API caller can finalize an incomplete or failed inspection with “Ready for resale”; backend does not check the submitted QA attestation, approver, deviation reason, or cosmetic completion. |
| **Critical** | **Inspection progress/completeness is calculated independently in the frontend.** | `WorkflowSteps` marks functional work complete when any manual result exists; evidence complete when at least one file exists; disposition complete when a field is non-empty; review complete from lifecycle string (`frontend/src/components/WorkflowSteps.tsx:63-88`). These do not describe all required checks. `GET /diagnostic-sessions/{id}` returns no authoritative completeness/next-action summary (`app/api/sessions/diagnostic_routes.py:622-659`). Several pages have their own distinct gates. |
| **High** | **Session-list response does not satisfy the frontend's full session type.** | API list returns only six fields (`app/api/sessions/diagnostic_routes.py:204-217`), whereas `DiagnosticSession` declares `technician_record`, `device_inventory`, and result maps (`frontend/src/api/execution.ts:5-18`). `getSessionDeviceName()`/`getSessionSerialNumber()` require `device_inventory` (`frontend/src/session/workflow.ts:54-72`); History repair/resale filters require `technician_record` (`frontend/src/pages/QcHistory.tsx:63-79`). List-row names/serials and these filters are unreliable until a detail fetch or summary response supplies the fields. |
| **High** | **Reports index can advertise sessions without a report.** | `GET /reports/` iterates every saved session and returns lifecycle status when report status/file is absent (`app/api/reports.py:21-45`). `/reports/{id}/json` separately returns 404 when no report exists (`app/api/reports.py:73-99`); `Reports.tsx` offers Preview for every returned row (`frontend/src/pages/Reports.tsx:18-25,66-82`). |
| **High** | **Cosmetic assessment has overlapping persistence representations.** | The manual catalog includes chassis/display/hinge/keyboard/port/physical cosmetic IDs (`app/diagnostics/manual_checks.py:3-27,173-175`), while detailed phase-based items are saved by `/cosmetic-inspection/{phase}` and separately serialized in `cosmetic_inspections` (`app/api/sessions/diagnostic_routes.py:52-95,661-686`). The main route currently renders the detailed component for cosmetic stage, but the manual endpoint still accepts overlapping results. Report summary/status logic reads manual outcomes separately from cosmetic items. Establish one technician-visible assessment and explicit legacy/data mapping before consolidating records. |
| **High** | **Evidence association is weaker than its item-level UI suggests.** | The upload client posts only session ID, file and confirmation (`frontend/src/api/evidence.ts:13-28`); the API accepts only optional diagnostic `run_id` (`app/api/evidence.py:39-46`). Cosmetic item evidence IDs are linked later by a separate session update (`frontend/src/pages/CosmeticInspection.tsx:340-370`), so upload success followed by assessment-save failure can leave session-level evidence not linked to the item. The general Photos page has no defect/check association. |
| **Medium** | **“Reports” and session history have different labels but shared records and incomplete search.** | `/sessions`, `/history`, `/active-qc`, `/reports` all consume the session list; report pages use session IDs. History searches only session ID/device/name/serial and exposes a narrow status filter (`frontend/src/pages/QcHistory.tsx:63-80,140-178`). Reports are sorted but not filterable (`frontend/src/pages/Reports.tsx:18-25`). Unify as Inspections and History & Reports with consistent search keys and explicit continue/report/reopen/retest actions. |
| **Medium** | **Intake suggests identity scanning/resolution that is not implemented.** | `DeviceDiscovery` labels the field “Asset tag / serial / barcode” but sends it as free-form `asset_tag` (`frontend/src/pages/DeviceDiscovery.tsx:447`); `AssetResolutionPicker` lists existing asset IDs from session rows and supports new/unresolved, but has no serial/tag resolution (`frontend/src/components/AssetResolutionPicker.tsx:13-63`). Backend verifies exact asset IDs (`diagnostic_session_service.py:112-164`). Clarify which identifier is authoritative and avoid implying scanner/lookup support. |
| **Medium** | **Displayed required-field policy is stronger than API validation.** | `FieldRequirements.tsx` lists approver, approval confirmation, and deviation reason as mandatory. `TechnicianRecordRequest` fields are optional (`app/api/sessions/diagnostic_routes.py:146-168`); only frontend requires approval and some fields; `finalize_session()` does not enforce those rules. Keep one shared server policy and render it. |
| **Medium** | **Storage configuration can make evidence routes unavailable.** | Python settings default to file mode, while all evidence routes call `_require_sqlite()` and return 409 otherwise (`app/core/config.py:30`, `app/api/evidence.py:30-36`). Supported Linux launchers and `.env.example` select SQLite; document/configure direct development launches consistently. |
| **Medium** | **Reopen and retest are conflated in the visible action.** | History says “Reopen for retest” but sends `POST /{id}/reopen`; service resets and reuses the same session (`frontend/src/pages/QcHistory.tsx:210-225`, `diagnostic_session_service.py:911-942`). Session creation separately supports `retest_of_session_id` and inheritance. Decide when to revise one inspection versus create a linked retest session; present distinct actions and preserve revision lineage. |
| **Low** | **Result status labels vary across pages and records.** | Report status, session lifecycle, diagnostic status, manual result and display attempt use separate vocabularies; shared UI maps only some aliases to pass/fail and otherwise neutral (`frontend/src/pages/Results.tsx:66-75`, `ReportViewer.tsx:32-42`, backend `DiagnosticStatus` and `TestStatus`). A neutral badge can hide why a result is unresolved. Use the authoritative summary with plain-language label, explanation and technician action. |
| **Low** | **Station identity is attribution, not an authenticated user.** | Setup and QA explicitly say names are records, not sign-in/authentication (`StationSetup.tsx:26-39`, `QaReview.tsx:224`). Keep this distinction visible; user/role enforcement requires a product decision, not a label change. |

## F. Proposed navigation

```text
UHDP
  Dashboard
  Start Inspection                 (primary action, not a technical module)
  Inspections                      (active, incomplete, awaiting decision)
  History & Reports                (search, report detail, reopen/retest)
  Settings
    Station setup
    Inspection requirements        (supervisor/admin, if configurable)
    Hardware inventory             (advanced station tool)
```

- **Dashboard:** replace the current inventory editor as the default technician landing page. Show Start Inspection, one prominent Continue Inspection when present, incomplete/awaiting-decision work, recently completed inspections, and station readiness.
- **Start Inspection:** keep device discovery and intake as a guided sequence, not a second “Hardware” navigation category. Require device confirmation; show identity before creating the session.
- **Inspections:** combine QC Sessions, Active QC, and incomplete rows from History. Resume by an explicit Continue action and show server-provided progress/next action.
- **Inspection workspace:** one route/concept with internal stages for automated checks, technician checks, physical condition, and review. Display Diagnostics remains a focused tool opened from its item.
- **History & Reports:** combine QC History, QC Reports, and report lookup. A row offers exactly the actions permitted by backend state: Continue, View report, Reopen, or Start linked retest.
- **Settings:** move Station Setup and Field Requirements out of primary task navigation. Move the editable hardware inventory to a station/device-detail tool.
- **Merge/simplify:** `/sessions` + `/active-qc` → Inspections; `/history` + `/reports` + report lookup → History & Reports; `/results` + `/qa` → Review & Disposition; `/photos` → contextual evidence in workspace, with optional general device photos.
- **Retain separately as internal routes/views:** report detail/print/export; display pattern test; station setup; hardware inventory. They need not be primary navigation concepts.
- **Remove from primary navigation:** standalone “Functional Inspection” and “Device Intake” links when an inspection is active; use Resume/Continue and the single workspace instead. Preserve old URLs via redirects until migration is verified.

This leaves five understandable destinations, with a single primary action, and does not expose backend modules as navigation.

## G. Proposed technician workflow

```text
Dashboard
  -> Start Inspection
       -> discover candidate devices
       -> explicitly confirm physical device identity
       -> resolve asset (existing match / create / allowed unresolved)
       -> enter required intake and work-order information
       -> create once; return persisted session/inspection ID
  -> Inspection Workspace
       -> server returns inspection plan, progress and next required action
       -> run automated tests
            -> show execution/progress
            -> persist each result; display outcome + meaning + next action
       -> perform technician-assisted checks
            -> instructions -> working / not working / unable to verify
            -> save notes/evidence against the check
       -> physical condition
            -> initial assessment -> item evidence -> save each item
            -> final comparison only when workflow rules require it
       -> Review & Disposition
            -> server summary, outstanding items, errors/reasons, evidence
            -> server-allowed dispositions and required rationale
            -> save decision / approval according to configured policy
            -> backend validates completeness and eligibility on finalization
  -> finalized record
       -> report generated from same persisted summary and revision
       -> View / print / export
  -> History & Reports
       -> search serial, asset tag, model, date, inspection, disposition
       -> Continue incomplete / View finalized report
       -> separately choose authorized Reopen same inspection or linked Retest
```

### Operational behavior to preserve

- Browser refresh and application restart must reload the backend session; browser `localStorage` may retain a draft or last-selected route, but must not be the only copy of inspection data.
- Failed saves must leave entered values visible as unsaved, retain retry inputs, and not show “saved” until the API confirms.
- No device candidate → explain discovery/permission checks and allow retry; multiple candidates → require explicit selection.
- Unsupported, blocked, inconclusive, failed, cancelled and not-applicable results must remain distinct; each non-pass result needs a reason and a clear next action.
- Session completion, inspection completeness, diagnostic outcome and disposition must be presented separately.

## H. Page-by-page redesign specification

The following are proposed views, not route or component changes. Reuse the current React/TypeScript, router, API client, CSS and UI primitives.

### H1. Dashboard

- **Purpose/objective:** choose the next piece of work or start inspection.
- **Display:** station identity and service readiness; Continue Inspection with device/model/serial, stage, progress and last saved time; inspections awaiting completion/decision; recent finalized work.
- **Primary action:** `Continue inspection` when resumable work exists; otherwise `Start inspection`.
- **Secondary actions/inputs:** open Inspections or History & Reports; no editable hardware fields here.
- **Backend:** list endpoint must return a lightweight authoritative summary per inspection; health/status and session routes already exist. Persisted session state remains backend-owned.
- **Validation/loading/error/empty:** loading skeleton; explicit backend offline/retry; empty state gives a Start Inspection button; no false offline/success defaults.
- **Navigation:** intake flow or exact saved inspection resume action.
- **Acceptance:** first view communicates what to do next; active work is one click away; inventory maintenance is not confused with inspection start.
- **Wireframe:**

  ```text
  Good morning, [technician]                 Station [id] · Local service ready
  [ Start Inspection ]

  CONTINUE INSPECTION
  [device/model] · Serial [value] · Stage: Technician checks
  [progress from server] · Saved [time]                [Continue]

  AWAITING ACTION                                      RECENTLY COMPLETED
  [inspection rows and next-action reasons]            [inspection rows]
  ```

### H2. Start Inspection / Device intake

- **Purpose/objective:** positively identify the physical machine and create one inspection for it.
- **Display:** candidate count; manufacturer/model/serial/asset tag and key inventory; advanced details collapsed.
- **Primary action:** `Confirm device and start inspection`.
- **Inputs:** explicit system-device selection, asset-resolution choice, required tag/work-order/technician fields. Do not promise barcode scanning unless implemented.
- **Backend:** current `GET /devices/`, `GET /diagnostic-sessions/`, `POST /diagnostic-sessions/`, `PUT /{id}/intake`; asset resolution may require a proper lookup API if business requirements require serial/tag search.
- **Validation:** require selection when multiple; visibly confirm the sole preselected candidate; validate exact existing asset match; make unresolved identity an explicit, policy-controlled choice.
- **States:** loading scan, no candidates with retry and permission guidance, multiple candidates with no implicit selection, save failure preserves values, successful confirmation only after create and intake persistence.
- **Navigation:** create once then open workspace at the first required stage. Resume existing intake must not create another session.
- **Acceptance:** refresh during a draft does not lose it; retry after ambiguous network response reuses the same idempotency key; selected identity cannot silently change.
- **Wireframe:**

  ```text
  START INSPECTION
  Select the computer on your bench
  ( ) Manufacturer · Model · Serial · Asset tag
  Device details ▾
  Asset identity: [match / create / unresolved, if allowed]
  Work order: [                 ]  Technician: [       ]
  [Confirm device and start inspection]
  ```

### H3. Inspections list

- **Purpose/objective:** find work to continue without choosing between Sessions, Active QC and History.
- **Display:** identity, inspection reference, technician, lifecycle, server progress, next action, last saved time.
- **Primary action:** `Continue`.
- **Secondary actions:** open report for finalized rows; permitted reopen/linked retest in a menu.
- **Backend:** expanded session-list summary; retrieve full detail before actions. Current list should not be treated as full session.
- **Validation/states:** stable empty/loading/error states; filter by actionable state; stale row uses fresh detail before navigation.
- **Navigation:** exact saved workspace stage from server `next_action`, not only browser localStorage.
- **Acceptance:** each in-progress session appears once; current device and serial come from server data; no duplicate Active QC card elsewhere.

### H4. Inspection workspace

- **Purpose/objective:** complete all plan-required checks in one inspection context.
- **Display:** confirmed device identity, inspection reference, server progress, stage list, grouped checks and persistent save/result status.
- **Primary action:** `Run next required check` or `Continue`; the server summary chooses the action.
- **Secondary actions:** retry supported runs, view advanced details, access report, save notes, stop/leave safely.
- **Inputs:** selected automated diagnostics, technician decisions/notes and specific test inputs, each tied to its check ID.
- **Backend:** current session GET, automated execution endpoints, manual-result endpoints, display endpoints and evidence API. The frontend needs a supported call to automated execution and a backend-produced plan/result contract; do not silently assume default test selection.
- **Validation:** render the existing backend outcome vocabulary; do not map “completed” to “passed”; require explicit notes only where policy says so; do not enable next stage based on “any result.”
- **Loading/error/empty:** show execution state and polling/progress; distinguish blocked by permission/device from unsupported; preserve retry data; empty plan should explain why no checks are required.
- **Navigation:** internal stages in one route; display tests return to the same checklist position; refresh reloads authoritative server state.
- **Acceptance:** all required items are visible; automated checks actually execute; every save updates progress from the server; session can be resumed from its next required action.
- **Wireframe:**

  ```text
  INSPECTION · [manufacturer model] · Serial [value]
  Overall progress: [server summary]      Last saved [time]
  [Automated tests] [Technician checks] [Physical condition] [Review]

  AUTOMATED TESTS
  Processor    [Not run]       [Run] / [Result + explanation]
  Memory       [Blocked: reason]             [Resolve / continue]

  TECHNICIAN CHECKS
  Keyboard     [instructions] [Working] [Not working] [Unable to verify]
               Notes [.....................] [Save]

  [Next required action]
  ```

### H5. Physical condition and evidence

- **Purpose/objective:** document initial physical state and, only when required, final state.
- **Display:** confirmed area/item checklist; condition/severity; damage description/location; prior assessment in final phase; attached evidence preview/link.
- **Primary action:** save/confirm the current item; continue when backend says the required stage is complete.
- **Inputs:** current condition fields, confirmation, notes and relevant photo. Make photo requirements policy-driven; no blanket assumption that every item needs a photo.
- **Backend:** current initial/final cosmetic endpoint and evidence upload/list/download. Preserve `evidence_ids` and session/run relationships; design an item/check association contract before changing evidence architecture.
- **Validation/states:** require description/location/severity for Damaged/Missing as current UI does; surface upload success separately from item-link save; if second write fails, preserve unlinked evidence state and offer retry/link recovery.
- **Navigation:** a workspace stage, with optional evidence in context; general device photos remain accessible in the same section.
- **Acceptance:** one technician-visible assessment for each concept; initial values remain immutable when final verification is recorded; report reproduces exact item/evidence association.

### H6. Review & Disposition

- **Purpose/objective:** understand inspection result and make a permissible disposition.
- **Display:** identity; lifecycle; completeness; outcomes by category; blocked/unsupported/inconclusive reasons; cosmetic summary; evidence; unresolved items; server recommendation and allowed dispositions.
- **Primary action:** `Save decision` then `Finalize inspection` only when server allows.
- **Inputs:** permitted disposition, reason when required, approver/attestation only as policy specifies.
- **Backend:** session summary and decision-eligibility policy must be authoritative. Current `PUT technician-record` and `POST finalize` need backend validation for the stated rules; React recommendation is not sufficient.
- **Validation:** rejected finalization returns machine-readable outstanding requirements that UI displays; failed persistence never reports success; finalization must bind to the report revision actually reviewed.
- **Loading/error/empty:** show why report/summary is missing; preserve unsaved decision; explain each blocked requirement.
- **Navigation:** one step after checks, then report detail.
- **Acceptance:** failed, incomplete, unsupported and inconclusive outcomes cannot be presented as ready for resale unless explicit server policy permits and records override rationale; finalized lifecycle is not styled as a passed outcome.
- **Wireframe:**

  ```text
  REVIEW INSPECTION
  Device [model / serial]         Lifecycle: Checks complete
  Completeness: [authoritative state]   Required [n] · Pending [n]

  RESULTS: Passed [n] · Failed [n] · Inconclusive [n] · Blocked [n]
  OUTSTANDING: [item and plain-language reason]
  PHYSICAL CONDITION: [summary and evidence]

  FINAL DECISION
  [server-allowed choices]   Reason [required only by policy]
  [Save decision] [Finalize inspection]
  ```

### H7. History & Reports

- **Purpose/objective:** find a previous inspection and choose the correct follow-up.
- **Display:** model, serial, asset tag, date, inspection ID, technician, lifecycle, completeness, disposition and report revision.
- **Primary action:** `Open` (Continue or View report based on backend state).
- **Secondary actions:** authorized reopen same inspection; create linked retest; export/print report; filters by date, model, serial, tag, status and disposition.
- **Backend:** list summary, full session detail, report JSON/HTML/revisions and reopen/retest APIs. Exclude rows without a report from report-only views or label the report as not generated.
- **Validation/states:** report 404 is an explicit no-report state; maintain retest ancestry; distinguish a finalized report from an editable inspection.
- **Navigation:** report detail or workspace.
- **Acceptance:** search works from server-supported data; every action says whether it continues, revises or creates a linked inspection; report history is visible.

### H8. Settings and station tools

- **Purpose/objective:** maintain workstation attribution, operational configuration and advanced hardware inventory.
- **Display:** station identity and persistence status; requirements/policy only for authorized supervisor role; technical inventory under an advanced station section.
- **Primary action:** save setting with explicit confirmation.
- **Backend:** station profile currently localStorage; hardware inventory API persists SQLite. Keep actual persistence labels distinct.
- **Validation/states:** identify local-only fields, handle corrupt/unavailable browser storage, show database errors for inventory writes.
- **Navigation:** dashboard or return to prior inspection without changing its state.
- **Acceptance:** technician does not need to visit settings to complete ordinary inspection; station identity is not represented as authenticated identity.

### H9. Report detail

- **Purpose/objective:** retain an immutable, understandable record of the reviewed inspection.
- **Display:** report revision, device/asset identity, disposition, completeness, result explanations, cosmetic details, associated evidence, finalization actor/time.
- **Primary action:** Print / Save PDF or Export JSON.
- **Backend:** existing report JSON/HTML/revision routes; fetch a specific finalized revision rather than silently showing latest mutable state.
- **States/navigation:** clear unavailable report, superseded revision and export failure states; return to History & Reports.
- **Acceptance:** screen, JSON and HTML represent the same report revision, status, disposition, test totals and evidence.

## I. Authoritative inspection state

### Current state boundary

The current session payload has lifecycle `status`, `intake_record`, planned diagnostic/manual arrays when supplied, diagnostic results, standardized `test_results`, `manual_results`, `display_diagnostic`, phase-keyed `cosmetic_inspections`, evidence metadata, technician record and report. `DiagnosticStatus` includes pending/running/passed/warning/failed/error/skipped/not-applicable/unsupported/inconclusive/cancelled; `TestStatus` additionally includes blocked and not-run (`app/hal/diagnostic_status.py`, `app/diagnostics/models/test_result.py`). These are outcomes, not lifecycle or final disposition.

The backend has partial completeness logic in `_session_result_status()` for planned diagnostic/manual IDs, and `/complete` uses report status to set lifecycle. But planned lists are optional, are not populated by the main intake form, and do not encompass all cosmetic/display/evidence requirements. The frontend therefore fills gaps with independent heuristics.

### Proposed contract

Prefer embedding an `inspection_summary` in `GET /diagnostic-sessions/{id}` and list responses, so all pages consume one calculation. Keep source records authoritative; compute the summary from the frozen persisted plan and persisted outcomes, and include a monotonically increasing session/report revision to identify the snapshot. Do not store duplicated counters as independent mutable state.

```json
{
  "session_id": "…",
  "revision": 12,
  "lifecycle_status": "checks_complete",
  "inspection_completeness": "incomplete",
  "plan": {
    "required": 39,
    "source": "service_center"
  },
  "progress": {
    "pending": 2,
    "in_progress": 0,
    "by_outcome": {
      "passed": 8,
      "failed": 1,
      "warning": 0,
      "inconclusive": 1,
      "blocked": 27,
      "unsupported": 0,
      "cancelled": 0,
      "not_applicable": 0,
      "not_run": 0
    }
  },
  "disposition": {
    "selected": null,
    "suggested": null,
    "allowed": [],
    "reason_required": false
  },
  "next_action": {
    "code": "resolve_blocked_checks",
    "label": "Review checks that could not be verified",
    "stage": "technician_checks"
  },
  "outstanding": [
    {
      "check_id": "usb_port",
      "label": "USB-A ports",
      "state": "blocked",
      "reason": "Technician was unable to verify"
    }
  ]
}
```

The counts above are illustrative only; the server must enforce and test that `required = pending + in_progress + sum(by_outcome)` for the frozen required plan, with optional checks reported separately. “Resolved” should not be used without defining whether blocked, unsupported, inconclusive and not-applicable are terminal for progress and acceptable for disposition.

### Four concepts the API and UI must keep separate

1. **Session lifecycle:** current values include created/running/incomplete/checks_complete/failed/completed; reopened sessions return to checks_complete. This describes workflow state, not hardware quality.
2. **Diagnostic outcome:** per-check canonical result. Keep PASS, FAIL, WARNING, INCONCLUSIVE, UNSUPPORTED, BLOCKED, CANCELLED, NOT_APPLICABLE, NOT_RUN distinct; show explanation and whether action is possible.
3. **Inspection completeness:** server-derived status over the inspection's frozen required plan, including cosmetic/display requirements defined by the selected workflow and persisted result/evidence policy.
4. **Final disposition:** the technician/supervisor decision stored in technician record. It is not inferred as a synonym for report status or lifecycle.

The backend must create/freeze the plan (from selected workflow/profile and agreed policy), define outcome-to-completeness/readiness rules, expose allowed dispositions/reason requirements, and reject finalization with a list of missing requirements. The frontend renders those facts and may validate for immediate feedback but must not be an independent decision engine. Report generation and finalization must use the exact same persisted summary/revision.

## J. Implementation sequence (approval required before any phase)

No phase below was implemented by this audit.

| Phase | Scope / likely files | Tests and acceptance | Dependency |
|---|---|---|---|
| **1. Authoritative workflow state** | Agree and persist/freeze a per-session required plan; calculate summary and next action in `app/services/diagnostic_session_service.py`; expose in `app/api/sessions/diagnostic_routes.py`; map existing result/cosmetic/display/evidence records without new duplicate counters. | API/service tests for every outcome, empty plan, missing/extra results, stale revision, incomplete/finalized/reopened states; verify progress arithmetic and finalization rejection. | Product policy decisions on required checks and how blocked/unsupported/inconclusive/N/A affect eligibility. Prerequisite to truthful progress and finalization. |
| **2. Navigation simplification** | `frontend/src/routes/index.tsx`, `components/Sidebar.tsx`, `Layout.tsx`, `WorkflowSteps.tsx`, `SessionContext.tsx`; route aliases for old deep links. | Build plus route/navigation tests using existing test setup if present; verify active route and browser refresh/resume. Acceptance: five simple destinations; active inspection is one click away; no duplicated top-level work lists. | Phase 1 contract identifies next stage and permitted actions. |
| **3. Device intake** | `Dashboard.tsx`, `DeviceDiscovery.tsx`, `AssetResolutionPicker.tsx`, `api/devices.ts`, `api/inventory.ts`, `api/execution.ts`; backend device/asset resolution only if product requires serial/tag lookup. | Device/API tests for zero/one/multiple system candidates, new/existing/unresolved asset, duplicate retry, intake-save failure and browser refresh. Acceptance: correct physical machine confirmed and one session created. | Phases 1–2; asset identity and unresolved policy. |
| **4. Unified inspection workspace** | `QcInspection.tsx`, `CosmeticInspection.tsx`, `diagnostics/display/*`, `components/layout/DiagnosticWorkspaceLayout.tsx`, API wrappers; connect existing automated execution routes. Backend changes only for the agreed plan/execution response. | Tests for actual automated call, manual result mapping, each status, retry/cancel, route return, reload and persistence. Acceptance: each required check is shown once with plain-language instructions/outcome. | Phases 1–3; diagnostic selection and execution policy. |
| **5. Cosmetic condition and evidence** | `CosmeticInspection.tsx`, `Photos.tsx`, `api/cosmeticInspection.ts`, `api/evidence.ts`, `app/api/evidence.py`, service persistence; resolve overlap with cosmetic manual checks and define item-level association. | Tests for initial/final preservation, damage-required fields, upload + link failure, ownership, SQLite/file configuration and report linkage. Acceptance: one physical-condition UX and evidence remains attached to its intended item/check. | Phase 1; policy for item set, photo requirements and storage backend. |
| **6. Review and disposition** | `Results.tsx`, `QaReview.tsx`, technician-record API and `finalize_session()`; backend owns recommendation/allowed dispositions and validations. | Service/API tests bypassing the UI for all invalid/missing conditions; stale report revision, disposition reason, approver policy, finalize and reopen. Acceptance: backend rejects disallowed finalization and returns actionable outstanding requirements. | Phase 1; explicit disposition, override and authorization policy. |
| **7. Reports and history** | `QcHistory.tsx`, `SessionOverview.tsx`, `ActiveQc.tsx`, `Reports.tsx`, `ReportViewer.tsx`, list/report APIs and frontend models. | Tests for list projection, search/filter, missing report, report revisions, linked retest, reopen and deleted record behavior. Acceptance: one search surface with correct resume/report/retest actions. | Phases 1 and 6; stable summary contract and report revision semantics. |
| **8. End-to-end technician acceptance** | Complete browser workflow, API and existing frontend/back-end test infrastructure; no new libraries unless separately approved. | Real browser interaction on isolated storage for passed, failed, blocked, unsupported, inconclusive, incomplete, interrupted/restarted, finalized, reopened and linked-retest cases. Include tests with multiple/no device candidates. | Phases 1–7. Requires a defined representative hardware/test fixture; never run disruptive stress tests without approval. |

## K. Evidence and limitations

### Directly inspected

- Current routes, layout/sidebar, all 14 page components and the display-diagnostic route in `frontend/src/routes/index.tsx`, `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/session/`, `frontend/src/api/`, and `frontend/src/diagnostics/display/`.
- Mounted route composition in `app/main.py`, API schemas/handlers in `app/api/`, the session orchestrator in `app/services/diagnostic_session_service.py`, manual/test result definitions, SQLite repositories/migrations, report APIs, evidence API, settings and Linux launchers.
- The requested `docs/UHDP_CODEBASE_MAP.md` exists but describes an older, smaller route map. `docs/UHDP_ARCHITECTURE.md` does not exist in this checkout. Current source was treated as authoritative over the older map.

### Test/build evidence

- Before this audit, against the same checkout, `pytest -c app/pytest.ini -q` completed with **563 passed, 39 warnings**; `cd frontend && npm run build` completed successfully (Vite 7.3.7). These establish regression/build results for this checkout, not hardware correctness or usability.
- `frontend/package.json` defines `dev`, `build`, and `preview`; it contains no frontend test or lint script. No UI test suite was run as part of this audit.
- `docs/UHDP_PHASE1_CLOSURE_PROGRESS.md` records a prior synthetic headless-Chromium Priority 4 flow and explicitly states automated hardware execution was not covered. That is historical evidence, not a browser run performed for this audit.

### Not exercised / inferred

- No live browser session, real technician usability session, physical hardware diagnostic, application restart scenario, network interruption, or current end-to-end workflow was run during this audit.
- Findings about API/UI mismatch and persistence behavior are source-derived. Existing tests may cover lower-level behaviors, but a passing suite does not prove that the current browser workflow is connected end to end.
- Disposition policy, required tests by workflow, final-cosmetic requirements, evidence requirements, shared-station authentication, unresolved asset policy, and whether retest should reuse or create a session require product/operations decisions.
- The audit did not inspect ignored or inaccessible runtime data, and did not open report artifacts. No claim is made about their contents.

## Preservation record

At audit start, `git status --short --branch --untracked-files=normal` reported:

```text
## main...origin/main [ahead 1]
?? data/Reports/
```

The current `HEAD` was `cbbb4b6`. The Phase 2 files listed as uncommitted in `UHDP_PHASE2_EXISTING_WORK_PRESERVATION.md` are now part of the current committed tree; that older preservation document records the earlier `30d6648` checkout and is historical. The untracked `data/Reports/` tree was already present at audit start and was not opened, staged, deleted, or changed.

This audit creates only `docs/UHDP_TECHNICIAN_FIRST_UX_AUDIT.md`. No source code, API contract, database schema, dependency, route, or other file was changed. No dependencies were installed. Nothing was staged or committed by the audit.

## Decisions needed before implementation

1. Which workflow/profile determines required automated, manual, display, cosmetic and evidence checks, and can technicians override it?
2. Which dispositions are allowed for failed, blocked, unsupported, inconclusive, not-run and not-applicable outcomes? What rationale/supervisor approval is required?
3. Does “retest” mean a new linked inspection, or reopen/revise the same inspection, and who may authorize each?
4. Is unresolved asset identity allowed for a completed inspection? Should serial/asset tag support real lookup or scanning?
5. Which cosmetic items are required for each device/workflow, and when are item photos mandatory?
6. Is technician/QA identity merely an audit label, or is authenticated role-based approval required?
7. Is SQLite mandatory for every supported technician deployment, given that evidence APIs require SQLite while direct Python settings default to file mode?

**Recommendation:** approve the information architecture and backend state/disposition policies before authorizing implementation. Do not begin a frontend rewrite until those rules and the authoritative inspection summary are agreed.
