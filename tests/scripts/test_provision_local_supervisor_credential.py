from __future__ import annotations

import os
from pathlib import Path
import stat

import pytest

from app.core.config import get_settings
from app.core.local_reopen_auth import verify_credential
from scripts import provision_local_supervisor_credential as provision


pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="Credential provisioning relies on Linux/POSIX file permissions.",
)


@pytest.fixture
def credential_setup(monkeypatch, tmp_path):
    data_directory = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_directory))
    get_settings.cache_clear()
    yield data_directory / "local_auth" / "supervisor.credential"
    get_settings.cache_clear()


def configure_password_prompts(monkeypatch, password: str) -> None:
    responses = iter((password, password))
    monkeypatch.setattr(provision.getpass, "getpass", lambda _prompt: next(responses))


def test_first_time_credential_provisioning_is_hashed_and_restrictive(
    credential_setup: Path,
    monkeypatch,
    capsys,
):
    password = "supervisor secret 123"
    configure_password_prompts(monkeypatch, password)

    assert provision.main([]) == 0
    output = capsys.readouterr()
    credential_hash = credential_setup.read_text(encoding="utf-8").strip()
    assert verify_credential(password, credential_hash)
    assert password not in output.out + output.err
    assert credential_hash not in output.out + output.err
    assert stat.S_IMODE(credential_setup.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(credential_setup.stat().st_mode) == 0o600


def test_existing_credential_is_refused_without_explicit_rotation(
    credential_setup: Path,
    monkeypatch,
    capsys,
):
    password = "supervisor secret 123"
    configure_password_prompts(monkeypatch, password)
    assert provision.main([]) == 0
    original = credential_setup.read_bytes()
    monkeypatch.setattr(
        provision.getpass,
        "getpass",
        lambda _prompt: pytest.fail("must not prompt for a refused replacement"),
    )

    assert provision.main([]) == 1
    assert credential_setup.read_bytes() == original
    assert "--rotate" in capsys.readouterr().err


def test_explicit_rotation_requires_confirmation_and_preserves_permissions(
    credential_setup: Path,
    monkeypatch,
):
    old_password = "supervisor secret 123"
    new_password = "replacement secret 456"
    configure_password_prompts(monkeypatch, old_password)
    assert provision.main([]) == 0
    original_mode = stat.S_IMODE(credential_setup.stat().st_mode)
    monkeypatch.setattr("builtins.input", lambda _prompt: "ROTATE")
    configure_password_prompts(monkeypatch, new_password)

    assert provision.main(["--rotate"]) == 0
    updated = credential_setup.read_text(encoding="utf-8").strip()
    assert verify_credential(new_password, updated)
    assert not verify_credential(old_password, updated)
    assert stat.S_IMODE(credential_setup.stat().st_mode) == original_mode == 0o600


def test_failed_atomic_rotation_leaves_existing_credential_unchanged(
    credential_setup: Path,
    monkeypatch,
):
    configure_password_prompts(monkeypatch, "supervisor secret 123")
    assert provision.main([]) == 0
    original = credential_setup.read_bytes()
    monkeypatch.setattr("builtins.input", lambda _prompt: "ROTATE")
    configure_password_prompts(monkeypatch, "replacement secret 456")
    monkeypatch.setattr(
        provision.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("simulated replace failure")),
    )

    with pytest.raises(OSError, match="simulated replace failure"):
        provision.main(["--rotate"])

    assert credential_setup.read_bytes() == original
    assert list(credential_setup.parent.glob(".supervisor.*.tmp")) == []
