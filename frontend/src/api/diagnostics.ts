import api from "./client";

export async function getDiagnostics(): Promise<string[]> {
    const response = await api.get(
        "/diagnostics/"
    );

    return response.data.diagnostics;
}
