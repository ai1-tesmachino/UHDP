import api from "./client";

export interface EvidenceMetadata {
    evidence_id: string;
    session_id: string;
    run_id: string | null;
    original_filename: string;
    media_type: string;
    size_bytes: number;
    sha256: string;
    created_at: string;
    sync_state?: string;
}

export async function uploadEvidence(sessionId: string, file: File) {
    const response = await api.post<EvidenceMetadata>(
        `/evidence/${encodeURIComponent(sessionId)}`,
        file,
        {
            headers: {
                "Content-Type": file.type || "application/octet-stream",
                "X-Filename": file.name,
                "X-UHDP-Confirmed": "true",
            },
            maxBodyLength: 100 * 1024 * 1024,
        },
    );
    return response.data;
}

export async function getSessionEvidence(sessionId: string) {
    const response = await api.get<EvidenceMetadata[]>(
        `/evidence/session/${encodeURIComponent(sessionId)}`,
    );
    return response.data;
}

export function getEvidenceUrl(evidenceId: string) {
    return `${api.defaults.baseURL}/evidence/${encodeURIComponent(evidenceId)}`;
}
