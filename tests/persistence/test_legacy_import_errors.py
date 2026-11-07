import hashlib

import pytest

from app.persistence.local.database import SQLiteDatabase
from app.persistence.local.import_legacy import import_legacy_files


def test_malformed_legacy_json_reports_source_and_preserves_input(tmp_path):
    sessions = tmp_path / "legacy-sessions"
    sessions.mkdir()
    source = sessions / "malformed.json"
    source.write_text("{invalid", encoding="utf-8")
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    database = SQLiteDatabase(tmp_path / "uhdp.sqlite3")

    with pytest.raises(ValueError, match="Invalid legacy JSON file") as error:
        import_legacy_files(database, [sessions], [])

    assert str(source) in str(error.value)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
