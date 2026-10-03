import api from "./client";

export interface RecentReport {
    session_id: string;
    device_id: string;
    status: string;
    created_at: string;
}

export async function getReports(): Promise<RecentReport[]> {
    const response = await api.get("/reports/");
    return response.data;
}

export async function getReport(sessionId: string) {
    const response = await api.get(
        `/reports/${encodeURIComponent(sessionId)}/json`
    );

    return response.data;
}

export async function saveTechnicianRecord(
    sessionId: string,
    record: {
        observed_issue: string;
        repair_performed: string;
        replacement_performed: string;
        customer_notes: string;
        refurbishment_grade: string;
    },
) {
    const response = await api.put(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/technician-record`,
        record,
    );
    return response.data;
}

export async function downloadReportJson(sessionId: string) {
    const response = await api.get(
        `/reports/${encodeURIComponent(sessionId)}/json`,
        { responseType: "blob" }
    );

    return response.data as Blob;
}

export function getReportHtmlUrl(sessionId: string) {
    return `${api.defaults.baseURL}/reports/${encodeURIComponent(sessionId)}/html`;
}
