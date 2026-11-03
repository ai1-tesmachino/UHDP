import api from "./client";

export interface DiagnosticSession {
    session_id: string;
    status: string;
    created_at: string;
    device_id?: string | null;
    intake_record?: Record<string, unknown>;
    technician_record?: Record<string, unknown>;
    test_results?: Record<string, unknown>;
    manual_results?: Record<string, unknown>;
    performance_results?: Record<string, unknown>;
    device_inventory?: Array<Record<string, unknown>>;
}

export async function createDiagnosticSession(
    deviceId?: string,
    intake?: {
        asset_tag?: string;
        technician?: string;
        station_id?: string;
        customer_reference?: string;
        workflow_type?: string;
        profile_name?: string;
        retest_of_session_id?: string;
        planned_diagnostics?: string[];
        planned_manual_checks?: string[];
    },
    sessionId?: string,
) {
    const payload = {
        ...(deviceId ? { device_id: deviceId } : {}),
        ...(intake || {}),
        ...(sessionId ? { session_id: sessionId } : {}),
    };
    const response = await api.post(
        "/diagnostic-sessions/",
        payload,
    );

    return response.data;
}

export async function getDiagnosticSession(sessionId: string): Promise<DiagnosticSession> {
    const response = await api.get(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}`,
    );
    return response.data;
}

export async function getDiagnosticSessions(): Promise<DiagnosticSession[]> {
    const response = await api.get("/diagnostic-sessions/");
    return response.data;
}

export async function updateSessionIntake(
    sessionId: string,
    deviceId: string,
    intake: Record<string, unknown>,
    deviceInventory: Array<Record<string, unknown>>,
) {
    const response = await api.put(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/intake`,
        {
            device_id: deviceId,
            intake_record: intake,
            device_inventory: deviceInventory,
        },
    );
    return response.data;
}

export async function executeDiagnostic(
    sessionId: string,
    deviceId: string,
    diagnostic: string,
    parameters: Record<string, number> = {},
) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/diagnostics/${encodeURIComponent(deviceId)}/${encodeURIComponent(diagnostic)}`,
        { parameters }
    );

    return response.data;
}

export interface ManualCheck {
    id: string;
    name: string;
    instructions: string;
}

export async function getManualChecks(): Promise<ManualCheck[]> {
    const response = await api.get("/diagnostic-sessions/manual-checks");
    return response.data.manual_checks;
}

export async function recordManualResult(
    sessionId: string,
    checkId: string,
    result: {
        outcome: "passed" | "failed" | "warning" | "not_applicable" | "blocked" | "not_run";
        notes: string;
        scan_status: "success" | "no_results" | "unsupported" | "error" | "not_attempted";
        detected_devices: string[];
        technician_decision: "working" | "not_working" | "unable_to_verify" | null;
        evidence: Record<string, unknown>;
    },
) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/manual/${encodeURIComponent(checkId)}`,
        result,
    );
    return response.data;
}

export async function completeDiagnosticSession(sessionId: string) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/complete`
    );

    return response.data;
}

export async function finalizeDiagnosticSession(sessionId: string) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/finalize`,
    );
    return response.data;
}

export async function reopenDiagnosticSession(sessionId: string) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/reopen`,
    );
    return response.data;
}

export async function runSession(
    sessionId: string,
    deviceId: string,
    diagnostics: string[],
) {
    const response = await api.post(
        `/diagnostic-sessions/${sessionId}/execute`,
        {
            diagnostics,
        },
        {
            params: {
                device_id: deviceId,
            },
        }
    );

    return response.data;
}