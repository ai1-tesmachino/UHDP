from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import shutil
import threading
import time
from datetime import UTC, datetime
import uuid

import psutil
import sqlite3

from app.core.config import get_settings
from app.persistence.local.database import SQLiteDatabase


TEST_FILE_SIZE_BYTES = 2 * 1024**3
BLOCK_SIZE_BYTES = 1024**2
FREE_SPACE_RESERVE_BYTES = 64 * 1024**2


class StorageBenchmarkService:
    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self._database = database or SQLiteDatabase()
        self._executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="uhdp-storage-benchmark",
        )
        self._lock = threading.Lock()
        self._active_targets: dict[str, str] = {}
        self._cancellations: dict[str, threading.Event] = {}
        self._futures: dict[str, Future[None]] = {}
        self._recover_interrupted_runs()

    def list_targets(self) -> list[dict[str, object]]:
        targets = []
        seen: set[str] = set()
        if os.name != "posix":
            return targets
        for partition in psutil.disk_partitions(all=False):
            device = partition.device
            mountpoint = partition.mountpoint
            if not device.startswith("/dev/") or not mountpoint or mountpoint in seen:
                continue
            seen.add(mountpoint)
            try:
                usage = psutil.disk_usage(mountpoint)
            except (OSError, PermissionError):
                continue
            target_id = _target_id(device, mountpoint)
            targets.append(
                {
                    "target_id": target_id,
                    "device_id": device,
                    "mountpoint": mountpoint,
                    "model": _device_model(device),
                    "capacity_bytes": usage.total,
                    "free_bytes": usage.free,
                    "filesystem": partition.fstype or "unknown",
                    "interface": _device_interface(device),
                }
            )
        return targets

    def start(
        self,
        target_id: str,
        *,
        confirmed: bool,
        cleanup_confirmed: bool,
        session_id: str | None = None,
    ) -> dict[str, object]:
        if not confirmed:
            raise ValueError("Technician confirmation is required.")
        if not cleanup_confirmed:
            raise ValueError("Explicit benchmark-file cleanup confirmation is required.")
        target = next(
            (item for item in self.list_targets() if item["target_id"] == target_id),
            None,
        )
        if target is None:
            raise ValueError("Selected storage target is not a mounted local device.")
        free_bytes = int(target["free_bytes"])
        if free_bytes < TEST_FILE_SIZE_BYTES + FREE_SPACE_RESERVE_BYTES:
            raise ValueError(
                "The selected filesystem does not have enough free space for the "
                "2 GiB test file and safety reserve."
            )
        benchmark_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()
        payload: dict[str, object] = {
            "benchmark_id": benchmark_id,
            "session_id": session_id,
            "status": "Running",
            "device_id": target["device_id"],
            "device_model": target["model"],
            "interface": target["interface"],
            "mountpoint": target["mountpoint"],
            "filesystem": target["filesystem"],
            "capacity_bytes": target["capacity_bytes"],
            "free_bytes_before": free_bytes,
            "file_size_bytes": TEST_FILE_SIZE_BYTES,
            "block_size_bytes": BLOCK_SIZE_BYTES,
            "started_at": started_at,
            "timestamp": started_at,
            "cleanup_confirmed": True,
            "checksum_verified": None,
        }
        with self._lock:
            if target_id in self._active_targets:
                raise ValueError("A storage benchmark is already running on this target.")
            cancellation = threading.Event()
            try:
                self._database.create_storage_benchmark(
                    benchmark_id,
                    str(target["device_id"]),
                    str(target["mountpoint"]),
                    payload,
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    "A storage benchmark is already running on this target."
                ) from exc
            self._active_targets[target_id] = benchmark_id
            self._cancellations[benchmark_id] = cancellation
            future = self._executor.submit(
                self._run,
                benchmark_id,
                target_id,
                target,
                payload,
                cancellation,
            )
            self._futures[benchmark_id] = future
        return payload

    def cancel(self, benchmark_id: str) -> bool:
        with self._lock:
            cancellation = self._cancellations.get(benchmark_id)
            if cancellation is None:
                return False
            cancellation.set()
            return True

    def get(self, benchmark_id: str) -> dict[str, object] | None:
        return self._database.get_storage_benchmark(benchmark_id)

    def history(
        self,
        device_id: str | None = None,
        limit: int = 100,
        session_id: str | None = None,
    ) -> list[dict[str, object]]:
        return self._database.list_storage_benchmarks(device_id, limit, session_id)

    def shutdown(self) -> None:
        with self._lock:
            cancellations = list(self._cancellations.values())
        for cancellation in cancellations:
            cancellation.set()
        self._executor.shutdown(wait=True, cancel_futures=False)

    def _run(
        self,
        benchmark_id: str,
        target_id: str,
        target: dict[str, object],
        payload: dict[str, object],
        cancellation: threading.Event,
    ) -> None:
        benchmark_directory: Path | None = None
        benchmark_file: Path | None = None
        benchmark_file_created = False
        final_status = "Failed"
        result = dict(payload)
        try:
            mountpoint = Path(str(target["mountpoint"])).resolve(strict=True)
            current_target = next(
                (
                    item
                    for item in self.list_targets()
                    if item["target_id"] == target_id
                    and Path(str(item["mountpoint"])).resolve(strict=True)
                    == mountpoint
                ),
                None,
            )
            if current_target is None:
                raise RuntimeError("Selected filesystem is no longer mounted.")
            uhdp_directory = mountpoint / ".uhdp"
            benchmark_directory = uhdp_directory / "benchmarks"
            if uhdp_directory.is_symlink() or benchmark_directory.is_symlink():
                raise RuntimeError("Benchmark directory must not be a symbolic link.")
            benchmark_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(benchmark_directory, 0o700)
            if benchmark_directory.resolve(strict=True).parent != uhdp_directory.resolve(
                strict=True
            ):
                raise RuntimeError("Benchmark directory resolved outside its safe location.")
            benchmark_file = benchmark_directory / f"uhdp-benchmark-{benchmark_id}.bin"
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(
                benchmark_file,
                flags,
                0o600,
            )
            benchmark_file_created = True
            write_checksum, write_duration = _write_test_file(
                descriptor, cancellation
            )
            if cancellation.is_set():
                final_status = "Interrupted"
                raise _BenchmarkInterrupted
            read_checksum, read_duration, cache_mode, cache_warning = _read_test_file(
                benchmark_file, cancellation
            )
            if cancellation.is_set():
                final_status = "Interrupted"
                raise _BenchmarkInterrupted
            verified = write_checksum == read_checksum
            result.update(
                {
                    "write_duration_seconds": write_duration,
                    "write_speed_mb_per_second": (
                        TEST_FILE_SIZE_BYTES / 1_000_000 / write_duration
                    ),
                    "read_duration_seconds": read_duration,
                    "read_speed_mb_per_second": (
                        TEST_FILE_SIZE_BYTES / 1_000_000 / read_duration
                    ),
                    "checksum_sha256": write_checksum,
                    "checksum_verified": verified,
                    "read_cache_mode": cache_mode,
                    "read_cache_warning": cache_warning,
                    "test_result": (
                        "Completed" if verified else "Checksum mismatch"
                    ),
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
            final_status = "Completed"
        except _BenchmarkInterrupted:
            result.update(
                {
                    "status": "Interrupted",
                    "test_result": "Interrupted by technician",
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
        except Exception as exc:
            result.update(
                {
                    "status": "Failed",
                    "test_result": "Benchmark failed",
                    "error": str(exc)[:1000],
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
        finally:
            if benchmark_file is not None and benchmark_file_created:
                try:
                    benchmark_file.unlink(missing_ok=True)
                    if benchmark_directory is not None:
                        _remove_empty_benchmark_directory(benchmark_directory)
                    result["cleanup_status"] = "Removed benchmark file"
                except OSError as exc:
                    result["cleanup_status"] = "Cleanup failed"
                    result["cleanup_error"] = str(exc)[:500]
                    if final_status == "Completed":
                        final_status = "Failed"
                        result["status"] = "Failed"
            result["status"] = final_status
            self._database.finish_storage_benchmark(
                benchmark_id,
                final_status,
                result,
            )
            session_id = result.get("session_id")
            if isinstance(session_id, str) and session_id:
                try:
                    from app.services.diagnostic_session_service import (
                        diagnostic_session_service,
                    )

                    diagnostic_session_service.record_performance_result(
                        session_id,
                        benchmark_id,
                        result,
                    )
                except Exception:
                    import logging

                    logging.getLogger(__name__).exception(
                        "Could not attach storage benchmark %s to QC session %s",
                        benchmark_id,
                        session_id,
                    )
            with self._lock:
                self._active_targets.pop(target_id, None)
                self._cancellations.pop(benchmark_id, None)
                self._futures.pop(benchmark_id, None)

    def _recover_interrupted_runs(self) -> None:
        for record in self._database.list_storage_benchmarks(limit=500):
            if record["status"] == "Running":
                data = record["data"]
                data.update(
                    {
                        "status": "Interrupted",
                        "test_result": "Backend restarted during benchmark.",
                        "completed_at": datetime.now(UTC).isoformat(),
                        "cleanup_status": (
                            "Temporary file may remain after interrupted process."
                        ),
                    }
                )
                self._database.finish_storage_benchmark(
                    str(record["benchmark_id"]),
                    "Interrupted",
                    data,
                )


class _BenchmarkInterrupted(Exception):
    pass


def _target_id(device: str, mountpoint: str) -> str:
    return hashlib.sha256(f"{device}\0{mountpoint}".encode()).hexdigest()[:24]


def _device_model(device: str) -> str | None:
    name = Path(device).name
    for candidate in (
        Path("/sys/class/block") / name / "device/model",
        Path("/sys/class/block") / name / "device/name",
    ):
        try:
            value = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    try:
        resolved = (Path("/sys/class/block") / name).resolve(strict=True)
    except OSError:
        return None
    for parent in resolved.parents:
        for field in ("model", "name"):
            try:
                value = (parent / "device" / field).read_text(
                    encoding="utf-8"
                ).strip()
            except OSError:
                continue
            if value:
                return value
    return None


def _device_interface(device: str) -> str | None:
    name = Path(device).name
    try:
        resolved = (Path("/sys/class/block") / name / "device").resolve(strict=True)
    except OSError:
        return None
    for parent in (resolved, *resolved.parents):
        if parent.name in {"nvme", "ata", "usb", "virtio", "mmc", "scsi"}:
            return parent.name
    return None


def _write_test_file(
    descriptor: int,
    cancellation: threading.Event,
) -> tuple[str, float]:
    digest = hashlib.sha256()
    block = os.urandom(BLOCK_SIZE_BYTES)
    remaining = TEST_FILE_SIZE_BYTES
    while remaining:
        size = min(BLOCK_SIZE_BYTES, remaining)
        digest.update(block[:size])
        remaining -= size
    checksum = digest.hexdigest()
    started = time.perf_counter()
    try:
        with os.fdopen(descriptor, "wb", buffering=0) as output:
            remaining = TEST_FILE_SIZE_BYTES
            while remaining:
                if cancellation.is_set():
                    raise _BenchmarkInterrupted
                size = min(BLOCK_SIZE_BYTES, remaining)
                _write_all(output, memoryview(block)[:size])
                remaining -= size
            output.flush()
            os.fsync(output.fileno())
        duration = time.perf_counter() - started
        return checksum, duration
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _read_test_file(
    path: Path,
    cancellation: threading.Event,
) -> tuple[str, float, str, str | None]:
    digest = hashlib.sha256()
    warning: str | None = None
    direct_descriptor: int | None = None
    if hasattr(os, "O_DIRECT"):
        try:
            direct_descriptor = os.open(path, os.O_RDONLY | os.O_DIRECT)
        except OSError as exc:
            warning = f"Direct I/O unavailable ({exc}); using cache-eviction hint."
    if direct_descriptor is not None:
        try:
            direct_digest = hashlib.sha256()
            duration = _read_direct(
                direct_descriptor,
                direct_digest,
                cancellation,
            )
            return (
                direct_digest.hexdigest(),
                duration,
                "O_DIRECT (page cache bypass)",
                None,
            )
        except OSError as exc:
            warning = f"Direct I/O read unavailable ({exc}); using cache-eviction hint."
        finally:
            os.close(direct_descriptor)

    with path.open("rb", buffering=0) as source:
        if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
            try:
                os.posix_fadvise(
                    source.fileno(),
                    0,
                    0,
                    os.POSIX_FADV_DONTNEED,
                )
                cache_mode = "POSIX_FADV_DONTNEED (best-effort cache eviction)"
            except OSError as exc:
                cache_mode = "cached read (physical-device throughput not established)"
                warning = f"Page-cache eviction hint failed: {exc}"
        else:
            cache_mode = "cached read (physical-device throughput not established)"
            warning = warning or "No supported page-cache control is available."
        started = time.perf_counter()
        while chunk := source.read(BLOCK_SIZE_BYTES):
            if cancellation.is_set():
                raise _BenchmarkInterrupted
            digest.update(chunk)
        duration = time.perf_counter() - started
    return digest.hexdigest(), duration, cache_mode, warning


def _write_all(output, block: memoryview) -> None:
    while block:
        written = output.write(block)
        if written is None or written <= 0:
            raise OSError(errno.EIO, "Benchmark file write made no progress.")
        block = block[written:]


def _read_direct(
    descriptor: int,
    digest: "hashlib._Hash",
    cancellation: threading.Event,
) -> float:
    libc = ctypes.CDLL(None, use_errno=True)
    buffer_pointer = ctypes.c_void_p()
    result = libc.posix_memalign(
        ctypes.byref(buffer_pointer),
        ctypes.c_size_t(4096),
        ctypes.c_size_t(BLOCK_SIZE_BYTES),
    )
    if result != 0:
        raise OSError(result, os.strerror(result))
    started = time.perf_counter()
    try:
        remaining = TEST_FILE_SIZE_BYTES
        while remaining:
            if cancellation.is_set():
                raise _BenchmarkInterrupted
            requested = min(BLOCK_SIZE_BYTES, remaining)
            received = libc.read(
                ctypes.c_int(descriptor),
                buffer_pointer,
                ctypes.c_size_t(requested),
            )
            if received < 0:
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error))
            if received == 0:
                raise OSError(errno.EIO, "Unexpected end of benchmark file.")
            digest.update(ctypes.string_at(buffer_pointer, received))
            remaining -= received
        return time.perf_counter() - started
    finally:
        libc.free(buffer_pointer)


def _remove_empty_benchmark_directory(directory: Path) -> None:
    try:
        directory.rmdir()
    except OSError:
        return
    parent = directory.parent
    try:
        parent.rmdir()
    except OSError:
        return
