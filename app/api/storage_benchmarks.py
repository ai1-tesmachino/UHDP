from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.services.storage_benchmark_service import StorageBenchmarkService


router = APIRouter(prefix="/storage-benchmarks", tags=["storage-benchmarks"])
_service: StorageBenchmarkService | None = None
_service_lock = threading.Lock()


def _get_service() -> StorageBenchmarkService:
    global _service
    with _service_lock:
        if _service is None:
            _service = StorageBenchmarkService()
        return _service


def shutdown_service() -> None:
    global _service
    with _service_lock:
        service = _service
        _service = None
    if service is not None:
        service.shutdown()


class StartBenchmarkRequest(BaseModel):
    target_id: str
    confirmed: bool
    cleanup_confirmed: bool
    session_id: str | None = None


@router.get("/targets")
def list_targets() -> list[dict[str, object]]:
    return _get_service().list_targets()


@router.get("/")
def list_benchmarks(
    device_id: str | None = None,
    session_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, object]]:
    return _get_service().history(device_id, limit, session_id)


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def start_benchmark(request: StartBenchmarkRequest, response: Response):
    try:
        benchmark = _get_service().start(
            request.target_id,
            confirmed=request.confirmed,
            cleanup_confirmed=request.cleanup_confirmed,
            session_id=request.session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    response.headers["Location"] = f"/storage-benchmarks/{benchmark['benchmark_id']}"
    return benchmark


@router.get("/{benchmark_id}")
def get_benchmark(benchmark_id: str) -> dict[str, object]:
    benchmark = _get_service().get(benchmark_id)
    if benchmark is None:
        raise HTTPException(status_code=404, detail="Benchmark not found.")
    return benchmark


@router.delete("/{benchmark_id}", status_code=status.HTTP_202_ACCEPTED)
def cancel_benchmark(benchmark_id: str) -> dict[str, bool]:
    if not _get_service().cancel(benchmark_id):
        raise HTTPException(
            status_code=404,
            detail="No running benchmark was found with that ID.",
        )
    return {"cancellation_requested": True}
