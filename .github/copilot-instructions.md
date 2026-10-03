# Copilot instructions for UHDP Phase 1 Production Starter

## Project shape

This repository is a paired backend/frontend application:

- Backend: FastAPI app under `app/`
- Frontend: React + TypeScript + Vite under `frontend/`
- Runtime and orchestration logic: `app/runtime/`, `app/services/`, `app/hal/`, and `app/workflows/`
- API routes are registered in `app/main.py` and `app/api/router.py`

The runtime is bootstrapped via `app.main:app`, which sets up a FastAPI app with a startup/shutdown lifecycle. The app starts an `Application` instance whose runtime lives in `app/runtime/context.py`, and the API layer is organized by feature area (`sessions`, `devices`, `reports`, `diagnostics`, `profiles`, `plugins`, etc.).

## Build, test, and validation commands

### Backend

Use a virtual environment before running backend commands:

```powershell
cd C:\Projects\UHDP_Phase1_Production
.\.venv\Scripts\activate
```

Run the API locally:

```powershell
uvicorn app.main:app --reload
```

Run one backend test:

```powershell
pytest tests/test_health.py -q
```

Run the full backend suite:

```powershell
pytest
```

`app/pytest.ini` sets `pythonpath = .`, `testpaths = tests`, and `asyncio_mode = auto`.

### Frontend

```powershell
cd C:\Projects\UHDP_Phase1_Production\frontend
npm install
npm run dev
```

Production build:

```powershell
cd C:\Projects\UHDP_Phase1_Production\frontend
npm run build
```

Preview the built app:

```powershell
cd C:\Projects\UHDP_Phase1_Production\frontend
npm run preview
```

There is no dedicated lint script configured in `frontend/package.json`, and there is no separate Python lint target in the repo configuration.

## Architecture notes

### Backend layering

The backend is organized around a runtime + API split:

- `app/main.py`: application bootstrap and CORS/middleware setup
- `app/api/`: HTTP endpoints and router registration
- `app/runtime/`: lifecycle, scheduler, workflow, event, and runtime context
- `app/hal/`: device and diagnostic abstraction layer
- `app/services/`: service-layer logic used by routes and runtime components
- `app/reports/` and `app/profiles/`: report/export and profile-related functionality
- `app/workflows/`: workflow definitions and execution support

When working in the backend, follow the existing feature folder pattern instead of introducing ad hoc top-level modules. Request handlers usually live in `app/api/...`, while supporting logic stays in service/runtime/hal modules.

### Frontend flow

The frontend is a Vite React app with browser routing managed in `frontend/src/App.tsx` and `frontend/src/routes/index.tsx`:

- `/` dashboard
- `/devices` device discovery
- `/diagnostics` diagnostic selection
- `/execution` execution screen
- `/results` results view
- `/report` report viewer

The frontend is separate from the backend but expected to call the FastAPI API from the same environment. Keep route and page components in `frontend/src/pages/` and shared layout/helpers in `frontend/src/components/` and `frontend/src/services/` as needed.

## Key conventions

- Keep API registrations centralized: new backend routes should be added in the appropriate `app/api/...` module and included from `app/main.py` or `app/api/router.py`.
- Treat the runtime lifecycle as the normal startup path: services and diagnostics are expected to initialize through the `Application`/`RuntimeContext` pattern rather than ad hoc global state.
- Maintain the existing separation of concerns: API routes should orchestrate, while domain/runtime functionality belongs in `services`, `runtime`, or `hal` layers.
- Use the repo’s discovered naming patterns: sessions, diagnostics, reports, devices, and workflows are the primary domain concepts.
- The project frequently uses `data/` as operational storage for generated/session artifacts, and the docs explicitly call out session/report flows as first-class paths through the application.

## Useful repo-specific references

- `README.md`: local startup instructions for the backend
- `docs/UHDP_CODEBASE_MAP.md`: architecture map and module ownership overview
- `app/pytest.ini`: Python test configuration
- `frontend/package.json`: frontend scripts and dependencies

