from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import tempfile
from typing import BinaryIO
import uuid

from app.core.config import get_settings
from app.persistence.local.database import SQLiteDatabase


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class EvidenceStorage:
    def __init__(
        self,
        database: SQLiteDatabase | None = None,
        root: str | Path | None = None,
        max_file_bytes: int = 100 * 1024 * 1024,
    ) -> None:
        settings = get_settings()
        self._database = database or SQLiteDatabase()
        self._root = Path(root or Path(settings.DATA_DIR) / "Evidence").resolve()
        self._max_file_bytes = max_file_bytes
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._root, 0o700)

    def store(
        self,
        session_id: str,
        stream: BinaryIO,
        *,
        filename: str,
        media_type: str,
        run_id: str | None = None,
    ) -> dict[str, object]:
        safe_session = _safe_component(session_id, "session_id")
        safe_run = _safe_component(run_id, "run_id") if run_id else None
        safe_filename = _safe_filename(filename)
        evidence_id = str(uuid.uuid4())
        boot_id = _safe_component(self._database.boot_session_id, "boot_session_id")
        parts = [
            "Boot_Sessions",
            f"BOOT_{boot_id}",
            f"QC_{safe_session}",
            "05_Evidence",
        ]
        if safe_run:
            parts.extend((f"RUN_{safe_run}", "Evidence"))
        directory = self._root.joinpath(*parts)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        final_path = directory / f"{evidence_id}_{safe_filename}"
        temporary_path: Path | None = None
        digest = hashlib.sha256()
        size = 0
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".incoming-",
                suffix=".tmp",
                dir=directory,
                delete=False,
            ) as output:
                temporary_path = Path(output.name)
                os.chmod(temporary_path, 0o600)
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self._max_file_bytes:
                        raise ValueError(
                            f"Evidence exceeds the {self._max_file_bytes}-byte limit."
                        )
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, final_path)
            temporary_path = None
            _fsync_directory(directory)
            relative_path = final_path.relative_to(self._root).as_posix()
            try:
                metadata = self._database.save_evidence_metadata(
                    evidence_id=evidence_id,
                    session_id=session_id,
                    run_id=run_id,
                    relative_path=relative_path,
                    original_filename=safe_filename,
                    media_type=media_type,
                    size_bytes=size,
                    sha256=digest.hexdigest(),
                )
            except BaseException:
                final_path.unlink(missing_ok=True)
                raise
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        return metadata

    def open(self, evidence_id: str) -> tuple[dict[str, object], BinaryIO]:
        metadata = self._database.get_evidence(evidence_id)
        if metadata is None:
            raise FileNotFoundError(evidence_id)
        relative = Path(str(metadata["relative_path"]))
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise RuntimeError("Stored evidence path is invalid.")
        file_path = (self._root / relative).resolve()
        if self._root not in file_path.parents:
            raise RuntimeError("Stored evidence path escapes the evidence directory.")
        digest = hashlib.sha256()
        with file_path.open("rb") as verification_stream:
            while chunk := verification_stream.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != metadata["sha256"]:
            raise RuntimeError("Stored evidence checksum verification failed.")
        return metadata, file_path.open("rb")


def _safe_component(value: str, field: str) -> str:
    if not _SAFE_COMPONENT.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"{field} contains unsupported characters.")
    return value


def _safe_filename(value: str) -> str:
    filename = value.replace("\\", "/").rsplit("/", 1)[-1]
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename).strip("._")
    if not filename:
        filename = "evidence.bin"
    return filename[:128]


def _fsync_directory(path: Path) -> None:
    if not hasattr(os, "O_DIRECTORY"):
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
