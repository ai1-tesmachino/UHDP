export interface ReportSummary {
    total: number;
    passed: number;
    failed: number;
    errors: number;
}

export interface DiagnosticReport {
    summary?: ReportSummary;
    data?: Record<string, unknown>;
    [key: string]: unknown;
}