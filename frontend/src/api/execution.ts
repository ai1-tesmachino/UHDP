import api from "./client";

export async function createDiagnosticSession() {
    const response = await api.post(
        "/diagnostic-sessions/"
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