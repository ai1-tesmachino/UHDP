import api from "./client";

export interface TestProfile {
    name: string;
    description: string;
    diagnostics: string[];
}

export interface ProfileDiagnosticResult {
    diagnostic_id: string;
    diagnostic_type: string;
    device_id: string;
    status: string;
    raw_status: string;
    execution_status: string;
    message: string;
    details: Record<string, unknown>;
    evaluation: unknown;
    created_at: string;
}

export interface ProfileExecutionResponse {
    profile_name: string;
    session_id: string;
    device_id: string;
    results: ProfileDiagnosticResult[];
    summary: Record<string, number>;
}

export async function getProfiles(): Promise<TestProfile[]> {
    const response = await api.get<TestProfile[]>("/profiles/");
    return response.data;
}

export async function executeProfile(
    profileName: string,
    sessionId: string,
    deviceId: string,
    diagnostics: string[],
    parameters: Record<string, Record<string, number>> = {},
): Promise<ProfileExecutionResponse> {
    const response = await api.post<ProfileExecutionResponse>(
        `/profiles/${encodeURIComponent(profileName)}/execute`,
        { diagnostics, parameters },
        { params: { session_id: sessionId, device_id: deviceId } },
    );
    return response.data;
}
