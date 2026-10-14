import api from "./client";

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
) {
    const response = await api.post(
        "/diagnostic-sessions/",
        deviceId ? { device_id: deviceId, ...intake } : undefined,
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
    outcome: "passed" | "failed" | "not_applicable" | "blocked" | "not_run",
    notes: string,
) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/manual/${encodeURIComponent(checkId)}`,
        { outcome, notes },
    );
    return response.data;
}

export async function completeDiagnosticSession(sessionId: string) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/complete`
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