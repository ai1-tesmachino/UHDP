import api from "./client";

export interface DiagnosticEngine {
    name: string;
    kind: string;
    available: boolean;
    status: string;
    path?: string;
}

export interface DiagnosticCapability {
    id: string;
    name: string;
    tier: string;
    engines: DiagnosticEngine[];
    available_engines: number;
    engine_count: number;
}

export interface CapabilityReport {
    platform: string;
    components: DiagnosticCapability[];
    oem_extension_points: string[];
}

export async function getCapabilities(): Promise<CapabilityReport> {
    const response = await api.get<CapabilityReport>("/capabilities/");
    return response.data;
}
