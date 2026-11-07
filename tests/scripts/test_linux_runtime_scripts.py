import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_regular_linux_launcher_uses_bundled_static_ui_server_without_vite():
    launcher = (ROOT / "scripts" / "run_uhdp_linux.sh").read_text(
        encoding="utf-8"
    )

    assert '[[ -f "$ROOT_DIR/frontend/dist/index.html" ]]' in launcher
    assert "API_PORT=8000" in launcher
    assert "UI_PORT=3000" in launcher
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
    assert '--sessions "$SESSIONS_DIRECTORY"' in launcher
    assert '--sessions "$ROOT_DIR/data/sessions"' in launcher
    assert '--reports "$REPORTS_DIRECTORY"' in launcher
    assert '--reports "$ROOT_DIR/data/reports"' in launcher


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


def test_normal_launcher_respects_environment_and_dotenv_storage_paths(tmp_path):
    installation = tmp_path / "installation"
    (installation / "scripts").mkdir(parents=True)
    (installation / "frontend/dist").mkdir(parents=True)
    (installation / ".venv/bin").mkdir(parents=True)
    (installation / "frontend/dist/index.html").touch()
    (installation / "scripts/serve_uhdp_ui.py").touch()
    shutil.copy2(
        ROOT / "scripts/run_uhdp_linux.sh",
        installation / "scripts/run_uhdp_linux.sh",
    )
    (installation / ".venv/bin/uvicorn").write_text(
        "#!/usr/bin/env bash\nexit 0\n",
        encoding="utf-8",
    )
    import_wrapper = installation / ".venv/bin/python"
    import_wrapper.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "$1" == "-m" && "$2" == "app.persistence.local.import_legacy" ]]; then\n'
        '  printf "IMPORT\\n" >> "$UHDP_TEST_IMPORT_LOG"\n'
        '  printf "ENV %s %s %s\\n" "$DATA_DIR" "$REPORTS_DIRECTORY" "$SESSIONS_DIRECTORY" '
        '>> "$UHDP_TEST_IMPORT_LOG"\n'
        '  printf "%s\\n" "$@" >> "$UHDP_TEST_IMPORT_LOG"\n'
        '  printf "END\\n" >> "$UHDP_TEST_IMPORT_LOG"\n'
        "  exit 0\n"
        "fi\n"
        'exec "$UHDP_REAL_PYTHON" "$@"\n',
        encoding="utf-8",
    )
    import_wrapper.chmod(0o755)
    (installation / ".venv/bin/uvicorn").chmod(0o755)
    (installation / ".env").write_text(
        "DATA_DIR=dotenv-data\n"
        "REPORTS_DIRECTORY=dotenv-reports\n"
        "SESSIONS_DIRECTORY=dotenv-sessions\n"
        "STORAGE_BACKEND=sqlite\n",
        encoding="utf-8",
    )
    import_log = tmp_path / "import.log"
    home = tmp_path / "home"
    home.mkdir()

    def run_launcher(overrides: dict[str, str]) -> list[str]:
        environment = os.environ.copy()
        for key in (
            "DATA_DIR",
            "REPORTS_DIRECTORY",
            "SESSIONS_DIRECTORY",
            "STORAGE_BACKEND",
            "SQLITE_DATABASE_PATH",
        ):
            environment.pop(key, None)
        environment.update({
            "HOME": str(home),
            "UHDP_REAL_PYTHON": sys.executable,
            "UHDP_TEST_IMPORT_LOG": str(import_log),
            **overrides,
        })
        completed = subprocess.run(
            ["bash", str(installation / "scripts/run_uhdp_linux.sh"), "--check-only"],
            cwd=installation,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr + completed.stdout
        invocations = import_log.read_text(encoding="utf-8").split("IMPORT\n")
        return invocations[-1].split("END\n", 1)[0].splitlines()

    dotenv_arguments = run_launcher({})
    assert "ENV dotenv-data dotenv-reports dotenv-sessions" in dotenv_arguments
    assert (installation / "dotenv-data").is_dir()
    assert (installation / "dotenv-reports").is_dir()
    assert (installation / "dotenv-sessions").is_dir()
    assert (installation / "data/reports") in [
        Path(argument) for argument in dotenv_arguments
    ]

    environment_arguments = run_launcher({
        "DATA_DIR": "environment-data",
        "REPORTS_DIRECTORY": "environment-reports",
        "SESSIONS_DIRECTORY": "environment-sessions",
    })
    assert (
        "ENV environment-data environment-reports environment-sessions"
        in environment_arguments
    )
    assert (installation / "environment-data").is_dir()
    assert (installation / "environment-reports").is_dir()
    assert (installation / "environment-sessions").is_dir()


def test_normal_launcher_reports_occupied_ports_before_importing_legacy_data(
    tmp_path,
):
    for port in ("8000", "3000"):
        installation = tmp_path / f"installation-{port}"
        (installation / "scripts").mkdir(parents=True)
        (installation / "frontend/dist").mkdir(parents=True)
        (installation / ".venv/bin").mkdir(parents=True)
        (installation / "frontend/dist/index.html").touch()
        (installation / "scripts/serve_uhdp_ui.py").touch()
        shutil.copy2(
            ROOT / "scripts/run_uhdp_linux.sh",
            installation / "scripts/run_uhdp_linux.sh",
        )
        (installation / ".venv/bin/uvicorn").write_text(
            "#!/usr/bin/env bash\nexit 0\n",
            encoding="utf-8",
        )
        (installation / ".venv/bin/uvicorn").chmod(0o755)
        python_wrapper = installation / ".venv/bin/python"
        python_wrapper.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "-m" && "$2" == "app.persistence.local.import_legacy" ]]; then\n'
            '  printf "IMPORT\\n" >> "$UHDP_TEST_IMPORT_LOG"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "-" && "$2" == "$UHDP_TEST_OCCUPIED_PORT" ]]; then\n'
            '  echo "simulated occupied port $2" >&2\n'
            "  exit 1\n"
            "fi\n"
            'exec "$UHDP_REAL_PYTHON" "$@"\n',
            encoding="utf-8",
        )
        python_wrapper.chmod(0o755)
        import_log = tmp_path / f"import-{port}.log"
        environment = os.environ.copy()
        for key in (
            "DATA_DIR",
            "REPORTS_DIRECTORY",
            "SESSIONS_DIRECTORY",
            "STORAGE_BACKEND",
            "SQLITE_DATABASE_PATH",
        ):
            environment.pop(key, None)
        environment.update({
            "HOME": str(tmp_path / f"home-{port}"),
            "XDG_STATE_HOME": str(tmp_path / f"state-{port}"),
            "XDG_CONFIG_HOME": str(tmp_path / f"config-{port}"),
            "XDG_CACHE_HOME": str(tmp_path / f"cache-{port}"),
            "UHDP_REAL_PYTHON": sys.executable,
            "UHDP_TEST_OCCUPIED_PORT": port,
            "UHDP_TEST_IMPORT_LOG": str(import_log),
            "DATA_DIR": str(tmp_path / f"data-{port}"),
            "REPORTS_DIRECTORY": str(tmp_path / f"reports-{port}"),
            "SESSIONS_DIRECTORY": str(tmp_path / f"sessions-{port}"),
            "STORAGE_BACKEND": "sqlite",
        })

        completed = subprocess.run(
            [
                "bash",
                str(installation / "scripts/run_uhdp_linux.sh"),
                "--no-browser",
            ],
            cwd=installation,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        assert completed.returncode != 0
        output = completed.stdout + completed.stderr
        assert f"Port {port} for " in output
        assert "is already in use" in output
        assert not import_log.exists()
        assert "Starting backend and frontend." not in output
