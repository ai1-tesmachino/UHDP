import api from "./client";

export interface TestProfile {
    name: string;
    description: string;
    diagnostics: string[];
}

export async function getProfiles(): Promise<TestProfile[]> {
    const response = await api.get<TestProfile[]>("/profiles/");
    return response.data;
}
