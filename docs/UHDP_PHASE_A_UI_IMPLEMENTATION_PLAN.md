# UHDP Phase A Technician-First UI Implementation Plan

**Phase:** A — frontend-only demo prototype  
**Status:** Inspection and planning complete; implementation is not started.

## 1. Existing frontend structure

- `frontend/src/main.tsx` mounts `App` and imports the global stylesheet `index.css`.
- `frontend/src/App.tsx` composes `BrowserRouter`, the station setup gate, `SessionProvider`, the application layout, routes, theme provider, tooltip provider, and toast notifications.
- `frontend/src/routes/index.tsx` registers the application pages and redirects `/diagnostics` to the current manual-check flow.
- `frontend/src/components/Layout.tsx`, `Sidebar.tsx`, and `Navbar.tsx` provide the shared shell and navigation. `components/layout/ApplicationLayout.tsx` re-exports the existing layout.
- `frontend/src/session/SessionContext.tsx` is an API-backed session provider. It creates and loads backend sessions, synchronizes active session IDs using `localStorage`, and refreshes an active session periodically. `session/workflow.ts` stores resume paths in `localStorage`.
- API clients live under `frontend/src/api/`; `api/client.ts` targets the FastAPI service on port 8000. Existing feature clients include execution, device, evidence, and report operations.
- Styling is based on the existing `src/index.css`, Tailwind v4/Vite integration, existing UI primitives, and a light/dark `ThemeProvider` (`src/theme/ThemeProvider.tsx`). The display diagnostic also has dedicated CSS in `src/diagnostics/display/displayDiagnostic.css`. Phase A should extend these conventions and preserve existing theme behavior.

## 2. Existing pages and routes

| Existing route/page | Current role | Phase A treatment |
|---|---|---|
| `/` — `pages/Dashboard.tsx` | Hardware inventory view/editor rather than a work queue | Rework into the technician dashboard. Do not expose inventory editing as the home task. |
| `/sessions` — `pages/SessionOverview.tsx` | Counts, active session, recent sessions | Fold active and recent demo inspections into `/inspections`. |
| `/active-qc` — `pages/ActiveQc.tsx` | Browser's active API session | Fold resume action into `/inspections`; do not use the backend session context. |
| `/devices` — `pages/DeviceDiscovery.tsx` | Device discovery, asset resolution, intake, and session creation | Adapt the useful identity/intake presentation to a demo-device selector and in-memory intake form. |
| `/qc` — `pages/QcInspection.tsx` or `pages/CosmeticInspection.tsx` | Manual functional checks or phase-based cosmetic inspection, selected by query parameter | Separate into the demo Physical Assessment, Hardware Diagnostics, and Technician Checks stages. |
| `/diagnostics/display/:sessionId` — `diagnostics/display/DisplayDiagnosticPage.tsx` | Interactive display tests backed by display/session APIs | Do not route the prototype through this API-backed page. Represent display as a simulated test in the demo diagnostics experience. |
| `/photos` — `pages/Photos.tsx` | Evidence upload and retrieval | Replace upload with optional sample/demo evidence placeholders within assessment items and reports. |
| `/results` and `/qa` — `pages/Results.tsx`, `pages/QaReview.tsx` | Report review and disposition are split across separate API-backed pages | Consolidate into Review Results and Final Disposition views over the same demo inspection state. |
| `/history`, `/reports`, `/report` — `pages/QcHistory.tsx`, `pages/Reports.tsx`, `pages/ReportViewer.tsx` | Overlapping API-backed session and report views | Consolidate list/search into `/history-reports`; open a demo report detail from a record. |
| `/setup`, `/settings/field-requirements` — `pages/StationSetup.tsx`, `pages/FieldRequirements.tsx` | Local station attribution and static requirements information | Consolidate useful station/theme information under `/settings`; avoid making setup a gate before the Dashboard. |

The existing route tree also includes a wildcard not-found page. During implementation, legacy URLs should either redirect to the corresponding demo destination or remain reachable as compatibility redirects; they must not mount API-backed workflow pages.

## 3. Existing reusable components and design foundation

- Reuse the shared `Layout`, `Sidebar`, and `Navbar` structure, updating navigation rather than creating a second shell.
- Reuse existing primitives under `frontend/src/components/ui/` and the installed Radix-based UI foundation. The current app already uses tooltip and alert-dialog primitives, `sonner`, and `lucide-react`; do not add packages or replace the design system.
- Reuse the identity/intake concepts from `DeviceDiscovery` and `AssetResolutionPicker`, but replace real inventory/session lookups with selectable seeded demo records.
- `WorkflowSteps` and the current `SessionContext` are tied to the existing session workflow; do not treat their API-backed state or completion heuristics as the demo source of truth. Add demo-specific progress derived from the demo model.
- Preserve `ThemeProvider` and existing global styles. Keep `DisplayCanvas`/display test logic out of the demo flow if it invokes session or diagnostic endpoints.

## 4. Pages requiring modification

- `App.tsx` and `routes/index.tsx`: introduce the four-destination prototype navigation and demo route tree. Prevent the station gate and API-backed `SessionProvider` from blocking or initiating backend work in the demo experience.
- `Layout.tsx`, `Sidebar.tsx`, and `Navbar.tsx`: expose only Dashboard, Inspections, History & Reports, and Settings as primary destinations; keep inspection stages within the inspection flow.
- `Dashboard.tsx`: replace the inventory-first content with actions, summary counts, and recent activity.
- `DeviceDiscovery.tsx`: reshape as demo intake, with identity confirmation and clearly marked simulated hardware details.
- `CosmeticInspection.tsx`: adapt to the requested grouped physical-condition assessment and optional demo evidence.
- `QcInspection.tsx`: adapt the manual checks to technician-confirmed demo results; keep these results distinct from simulated automated results.
- `Results.tsx` and `QaReview.tsx`: use a shared demo summary and disposition state instead of API report/technician-record calls.
- `QcHistory.tsx`, `Reports.tsx`, and `ReportViewer.tsx`: use demo records and a consolidated history/report experience.
- `StationSetup.tsx` and `FieldRequirements.tsx`: retain only useful existing technician/station settings; do not add backend configuration or authentication.

## 5. Pages/components requiring creation

- `/inspections`: active and incomplete demo inspections with Continue and View Details actions.
- `/history-reports`: consolidated demo history, status/disposition filters, and report opening.
- A simulated Hardware Diagnostics view for CPU, memory, storage, battery, graphics, and display tests; it must not use the current display/session API page.
- A demo-state provider/reducer and typed presentation models, kept separate from production API types.
- Reusable demo-oriented elements as needed: demo-mode banner, inspection progress/stage navigation, diagnostic result/status presentation, and report detail. Prefer extending existing components over duplicating them.

## 6. Proposed navigation

```text
UHDP
├── Dashboard
├── Inspections
├── History & Reports
└── Settings
```

Starting a new inspection is a prominent Dashboard action that begins at Device Intake. Physical Assessment, Hardware Diagnostics, Technician Checks, Review Results, and Final Disposition are stages inside an inspection, not sidebar destinations.

## 7. Proposed technician workflow

1. **Dashboard:** show start/resume actions, demo summary counts, and recent activity.
2. **Device Intake:** select a seeded device, review detected demo specifications, enter/edit asset details, and confirm identity. Flag missing serials or unresolved identity; do not imply that demo edits affect real hardware.
3. **Physical Assessment:** assess grouped display, body, hinges/enclosure, keyboard/touchpad appearance, and ports; allow Good, Minor damage, Major damage, Not applicable, or Not inspected, with optional sample evidence.
4. **Hardware Diagnostics:** run predefined, short simulations with visible Running and terminal demo statuses; show result details without device access.
5. **Technician Checks:** record Working, Not working, Unable to verify, or Not applicable and an optional note. Visually distinguish these confirmations from simulated automated tests.
6. **Review Results:** summarize identity, physical condition, automated outcomes, technician checks, evidence placeholders, and outstanding demo work.
7. **Final Disposition:** offer the five requested dispositions, an optional explanation, and a confirmation summary. Label completion as simulated, not a real finalization.
8. **History & Reports:** browse seeded completed/incomplete/failure/defect scenarios and open a demo report.

## 8. Demo data and state architecture

- Add a centralized `frontend/src/demo/` module with typed demo-domain types and seeded device, inspection, diagnostic, technician-check, and report data. Split files by domain only where it improves clarity; keep records out of page components.
- Keep demo domain types independent of `frontend/src/api/*` production request/response types.
- Use a demo-specific React context/reducer as the sole mutable source for the in-progress prototype. Navigation between stages preserves state while the app remains open.
- Use in-memory state only for Phase A. A visible demo notice should explain that a full refresh restores the seeded demo state and that interactions are temporary.
- Ensure prototype routes/components do not import or call API clients, `SessionContext`, evidence/report endpoints, or real device discovery. Do not execute shell commands, access hardware, or write demo records to localStorage, sessionStorage, SQLite, or backend services. Existing theme/station preferences are separate from demo inspection state.
- Do not add dependencies, alter `package.json`, modify backend files, or change schemas/services.

## 9. Implementation sequence

1. **Completed in this phase:** inspect the current frontend and record this plan. No application code has been changed.
2. After approval, establish the demo state boundary and replace the shared navigation/shell destinations.
3. Implement the Dashboard and Inspections list.
4. Adapt Device Intake and Physical Assessment.
5. Build simulated Hardware Diagnostics and Technician Checks.
6. Consolidate Review Results and Final Disposition.
7. Consolidate History & Reports and add demo report detail.
8. Simplify Settings using existing station/theme structures.
9. Run `npm run build`, `git diff --check`, and a full browser walkthrough of the demo flow, navigation/state retention, historical reports, and refresh-reset notice. Verify no API requests or hardware access occur and no backend/database/dependency files changed.

The current `frontend/package.json` defines `dev`, `build`, and `preview`; there is no dedicated test or lint script. The Vite production build is the required automated validation, with the demo workflow checked manually in the browser.
