import time
import threading
from typing import Callable

import psutil

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.stress_utils import stress_test_duration


MAX_ALLOCATION_BYTES = 512 * 1024 * 1024


class MemoryStressDiagnostic:
    def execute(
        self,
        request: DiagnosticRequest,
        cancellation: threading.Event | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DiagnosticResult:
        duration = stress_test_duration(request)
        available_bytes = psutil.virtual_memory().available
        allocation_bytes = min(
            available_bytes // 2,
            MAX_ALLOCATION_BYTES,
        )

        def cancelled_result() -> DiagnosticResult:
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.CANCELLED,
                message="Memory stress was cancelled before readback completed",
                details={
                    "duration_seconds": duration,
                    "allocation_bytes": allocation_bytes,
                    "available_bytes_before_test": available_bytes,
                    "allocation_limit_bytes": MAX_ALLOCATION_BYTES,
                    "readback_complete": False,
                    "stress_test": True,
                },
            )

        if cancellation is not None and cancellation.is_set():
            return cancelled_result()

        if allocation_bytes < 16 * 1024 * 1024:
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.NOT_APPLICABLE,
                message="Insufficient available memory for the minimum bounded allocation",
                details={
                    "available_bytes": available_bytes,
                    "minimum_allocation_bytes": 16 * 1024 * 1024,
                    "stress_test": True,
                },
            )

        started = time.monotonic()
        try:
            buffer = bytearray(allocation_bytes)
            page_count = (allocation_bytes + 4095) // 4096
            for page_index, offset in enumerate(range(0, allocation_bytes, 4096)):
                if cancellation is not None and cancellation.is_set():
                    return cancelled_result()
                buffer[offset] = (offset // 4096) & 0xFF
                if progress_callback and page_index % 4096 == 0:
                    progress_callback(min(75, int(page_index * 75 / page_count)))
            deadline = started + duration
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                if cancellation is not None and cancellation.wait(min(0.25, remaining)):
                    return cancelled_result()
                time.sleep(0)
            mismatches = 0
            checksum = 0
            for page_index, offset in enumerate(range(0, allocation_bytes, 4096)):
                if cancellation is not None and cancellation.is_set():
                    return cancelled_result()
                expected = (offset // 4096) & 0xFF
                actual = buffer[offset]
                checksum += actual
                if actual != expected:
                    mismatches += 1
                if progress_callback and page_index % 4096 == 0:
                    progress_callback(min(99, 75 + int(page_index * 24 / page_count)))
        except MemoryError:
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.ERROR,
                message="Operating system refused the bounded memory allocation",
                details={
                    "requested_allocation_bytes": allocation_bytes,
                    "available_bytes": available_bytes,
                    "stress_test": True,
                },
            )

        return DiagnosticResult(
            diagnostic_id=request.diagnostic_id,
            diagnostic_type=request.diagnostic_type,
            device_id=request.device_id,
            status=(
                DiagnosticStatus.FAILED
                if mismatches
                else DiagnosticStatus.PASSED
            ),
            message=(
                "Memory readback detected pattern mismatches"
                if mismatches
                else "Bounded memory allocation and readback completed"
            ),
            details={
                "duration_seconds": duration,
                "allocation_bytes": allocation_bytes,
                "available_bytes_before_test": available_bytes,
                "allocation_limit_bytes": MAX_ALLOCATION_BYTES,
                "checksum": checksum,
                "pattern_mismatches": mismatches,
                "readback_complete": True,
                "stress_test": True,
            },
        )
