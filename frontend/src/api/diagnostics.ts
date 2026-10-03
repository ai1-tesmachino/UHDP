import api from "./client";

export async function getDiagnostics(): Promise<string[]> {
    const response = await api.get(
        "/diagnostics/"
    );

    return response.data.diagnostics;
}

export async function executeDiagnostic(
    deviceId: string,
    diagnosticType: string
) {
    const response = await api.post(
        "/diagnostics/execute",
        {
            device_id: deviceId,
            diagnostic_type: diagnosticType,
        }
    );

    return response.data;
}
