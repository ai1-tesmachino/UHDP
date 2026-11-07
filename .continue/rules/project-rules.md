---
name: UHDP Development and Safety
alwaysApply: true
---

# UHDP Development and Safety

- Inspect the relevant implementation and tests before changing behavior. Preserve existing user changes and established project patterns.
- For UHDP questions, use repository source and local documentation first. Use web search only when local evidence is insufficient or the user requests current external information.
- Keep backend changes within the existing FastAPI feature structure and frontend changes within the React/Vite structure. Preserve API contracts between them.
- Put tests in `tests/`. Use `python -m pytest -c app/pytest.ini tests` for backend checks and the scripts in `frontend/package.json` for frontend checks.
- Do not expose or commit secrets. Keep credentials in backend environment configuration, never frontend code.
- Do not reset or delete operational data, databases, or reports. Use isolated test data.
- Hardware stress tests and other potentially disruptive diagnostics require explicit user approval.
- Ask before installing dependencies, changing system configuration, or performing destructive Git or deployment operations.
