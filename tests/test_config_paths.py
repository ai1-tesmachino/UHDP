from app.core.config import Settings


def test_settings_derive_local_paths_from_environment_data_directory(
    tmp_path,
    monkeypatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text("DATA_DIR=dotenv-data\n", encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", "environment-data")
    for key in ("REPORTS_DIRECTORY", "SESSIONS_DIRECTORY"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=env_file)

    assert settings.DATA_DIR == "environment-data"
    assert settings.REPORTS_DIRECTORY == "environment-data/reports"
    assert settings.SESSIONS_DIRECTORY == "environment-data/sessions"


def test_explicit_environment_storage_paths_override_dotenv_paths(
    tmp_path,
    monkeypatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATA_DIR=dotenv-data\n"
        "REPORTS_DIRECTORY=dotenv-reports\n"
        "SESSIONS_DIRECTORY=dotenv-sessions\n"
        "SQLITE_DATABASE_PATH=dotenv.sqlite3\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATA_DIR", "environment-data")
    monkeypatch.setenv("REPORTS_DIRECTORY", "environment-reports")
    monkeypatch.setenv("SESSIONS_DIRECTORY", "environment-sessions")
    monkeypatch.setenv("SQLITE_DATABASE_PATH", "environment.sqlite3")

    settings = Settings(_env_file=env_file)

    assert settings.DATA_DIR == "environment-data"
    assert settings.REPORTS_DIRECTORY == "environment-reports"
    assert settings.SESSIONS_DIRECTORY == "environment-sessions"
    assert settings.SQLITE_DATABASE_PATH == "environment.sqlite3"
