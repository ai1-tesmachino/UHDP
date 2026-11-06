from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_regular_linux_launcher_uses_bundled_static_ui_server_without_vite():
    launcher = (ROOT / "scripts" / "run_uhdp_linux.sh").read_text(
        encoding="utf-8"
    )

    assert '[[ -f "$ROOT_DIR/frontend/dist/index.html" ]]' in launcher
    assert 'API_URL="http://127.0.0.1:8000"' in launcher
    assert '"$ROOT_DIR/.venv/bin/uvicorn" app.main:app' in launcher
    assert '"$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/scripts/serve_uhdp_ui.py" &' in (
        launcher
    )
    assert 'wait_for_service "Backend API" "${API_URL}/health/" "api"' in launcher
    assert 'wait_for_service "Frontend" "$UI_URL" "ui"' in launcher
    assert "vite" not in launcher.lower()
    assert "node_modules" not in launcher.lower()
    api_client = (ROOT / "frontend" / "src" / "api" / "client.ts").read_text(
        encoding="utf-8"
    )
    assert "`${window.location.protocol}//${apiHost}:8000`" in api_client


def test_live_launcher_uses_persistent_sqlite_and_imports_json_before_backend():
    launcher = (ROOT / "scripts" / "run_uhdp_live.sh").read_text(
        encoding="utf-8"
    )

    sqlite_selection = 'export STORAGE_BACKEND="sqlite"'
    importer = '"$UHDP_ROOT/.venv/bin/python" -m app.persistence.local.import_legacy'
    backend = '"$UHDP_ROOT/.venv/bin/uvicorn" app.main:app'
    assert sqlite_selection in launcher
    assert 'export SQLITE_DATABASE_PATH="${DATA_ROOT}/uhdp.sqlite3"' in launcher
    assert importer in launcher
    assert '--sessions "$SESSIONS_DIRECTORY"' in launcher
    assert '--reports "$REPORTS_DIRECTORY"' in launcher
    assert launcher.index(importer) < launcher.index(backend)
    assert '"$UHDP_ROOT/.venv/bin/python" "$UHDP_ROOT/scripts/serve_uhdp_ui.py" &' in (
        launcher
    )
    assert "python3 " not in launcher
