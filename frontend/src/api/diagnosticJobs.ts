import api from "./client";

export type DiagnosticJobType =
    | "cpu_stress"
    | "memory_stress"
    | "gpu_stress"
    | "battery_endurance";

export interface DiagnosticJob {
    job_id: string;
    test_type: DiagnosticJobType;
    device_id: string;
    session_id?: string | null;
    state: "queued" | "running" | "completed" | "failed" | "cancelled";
    progress_percent: number;
    created_at: string;
    started_at?: string | null;
    completed_at?: string | null;
    criteria_profile: {
        version: string;
        criteria: Record<string, number>;
    };
    latest_measurement?: Record<string, unknown> | null;
    measurement_history?: Array<Record<string, unknown>>;
    result?: {
        evaluation_status?: string;
        evaluation_message?: string;
        measurements?: Record<string, unknown>;
        details?: Record<string, unknown>;
        message?: string;
        [key: string]: unknown;
    } | null;
    error?: string | null;
}

export async function createDiagnosticJob(
    payload: {
        test_type: DiagnosticJobType;
        device_id: string;
        session_id?: string;
        parameters: Record<string, number | string>;
        criteria: Record<string, number>;
    },
): Promise<DiagnosticJob> {
    const response = await api.post("/diagnostic-jobs/", payload);
    return response.data;
}

export async function getDiagnosticJobs(): Promise<DiagnosticJob[]> {
    const response = await api.get("/diagnostic-jobs/");
    return response.data.jobs;
}

export async function getDiagnosticJob(jobId: string): Promise<DiagnosticJob> {
    const response = await api.get(`/diagnostic-jobs/${encodeURIComponent(jobId)}`);
    return response.data;
}

export async function cancelDiagnosticJob(jobId: string): Promise<DiagnosticJob> {
    const response = await api.post(
        `/diagnostic-jobs/${encodeURIComponent(jobId)}/cancel`,
    );
    return response.data;
}
