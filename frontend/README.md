# UHDP Frontend

React 19, TypeScript, and Vite interface for the UHDP FastAPI diagnostic service.

## Run locally

From the repository root, start the API with `uvicorn app.main:app --reload`, then
start the UI from `frontend/` with `npm run dev`. Vite serves the interface on
`http://localhost:3000`; the API client uses `http://localhost:8000`.

## Technician flow

The UI routes through station setup, device discovery/intake, backend profile
selection, automated or guided manual checks, results, QA disposition, and report
export. Technician/station identity is stored in the current browser profile and
included in new session intake. It is a station record, not authenticated login.

Profiles, inventory, diagnostic results, manual-check outcomes, session reports,
and report exports are read from or written to the existing backend APIs. JSON
and HTML exports use the report service; PDF output uses the browser's Print /
Save as PDF workflow because the backend does not currently expose a PDF export.
The UI labels hardware details that the current discovery/diagnostic APIs do not
provide rather than inventing module or drive measurements.
