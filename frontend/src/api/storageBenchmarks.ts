import api from "./client";

export interface StorageBenchmarkTarget {
    target_id: string;
    device_id: string;
    mountpoint: string;
    model: string | null;
    capacity_bytes: number;
    free_bytes: number;
    filesystem: string;
    interface: string | null;
}

export interface StorageBenchmark {
    benchmark_id: string;
    session_id?: string | null;
    device_id: string;
    mountpoint: string;
    status: "Running" | "Completed" | "Interrupted" | "Failed";
    started_at: string;
    completed_at: string | null;
    data: Record<string, unknown>;
}

export async function getStorageBenchmarkTargets() {
    const response = await api.get<StorageBenchmarkTarget[]>("/storage-benchmarks/targets");
    return response.data;
}

export async function getStorageBenchmarks(deviceId?: string, sessionId?: string) {
    const response = await api.get<StorageBenchmark[]>("/storage-benchmarks/", {
        params: {
            ...(deviceId ? { device_id: deviceId } : {}),
            ...(sessionId ? { session_id: sessionId } : {}),
        },
    });
    return response.data;
}

export async function startStorageBenchmark(targetId: string, sessionId?: string) {
    const response = await api.post<StorageBenchmark>("/storage-benchmarks/", {
        target_id: targetId,
        confirmed: true,
        cleanup_confirmed: true,
        ...(sessionId ? { session_id: sessionId } : {}),
    });
    return response.data;
}

export async function getStorageBenchmark(benchmarkId: string) {
    const response = await api.get<StorageBenchmark>(
        `/storage-benchmarks/${encodeURIComponent(benchmarkId)}`,
    );
    return response.data;
}

export async function cancelStorageBenchmark(benchmarkId: string) {
    const response = await api.delete(
        `/storage-benchmarks/${encodeURIComponent(benchmarkId)}`,
    );
    return response.data;
}
