import api from "./client";
import type { CosmeticInspections } from "./cosmeticInspection";

export interface DiagnosticSession {
    session_id: string;
    status: string;
    created_at: string;
    device_id?: string | null;
    asset_id?: string | null;
    intake_record?: Record<string, unknown>;
    technician_record?: Record<string, unknown>;
    test_results?: Record<string, unknown>;
    manual_results?: Record<string, unknown>;
    cosmetic_inspections?: CosmeticInspections;
    performance_results?: Record<string, unknown>;
    display_diagnostic?: DisplayDiagnostic | null;
    device_inventory?: Array<Record<string, unknown>>;
}

export interface DiagnosticSessionIntake {
    asset_tag?: string;
    technician?: string;
    station_id?: string;
    customer_reference?: string;
    workflow_type?: string;
    asset_id?: string;
    create_asset?: boolean;
    profile_name?: string;
    retest_of_session_id?: string;
    planned_diagnostics?: string[];
    planned_manual_checks?: string[];
}

export type AssetResolutionSelection =
    | { mode: "existing"; assetId: string }
    | { mode: "new" }
    | { mode: "unresolved" };

export function assetResolutionRequestFields(
    selection: AssetResolutionSelection,
): { asset_id?: string; create_asset: boolean } {
    if (selection.mode === "existing") {
        const assetId = selection.assetId.trim();
        if (!assetId) throw new Error("Enter an existing asset ID to link to this QC session.");
        return { asset_id: assetId, create_asset: false };
    }
    return { create_asset: selection.mode === "new" };
}

export function assetResolutionConfirmed(
    assetId: unknown,
    selection: AssetResolutionSelection,
): boolean {
    if (selection.mode === "existing") return assetId === selection.assetId.trim();
    if (selection.mode === "new") return typeof assetId === "string" && assetId.length > 0;
    return assetId == null;
}

export type DisplayTestOutcome = "passed" | "failed" | "inconclusive" | "skipped";

export interface DisplayTestResult {
    test_id: string;
    test_name: string;
    attempt_id: string;
    attempt_number: number;
    status: DisplayTestOutcome;
    notes: string;
    defects: Array<{
        type: string;
        location: string;
        count?: number | null;
    }>;
    started_at: string;
    completed_at: string;
    duration_seconds: number;
}

export interface DisplayTestAttempt {
    attempt_id: string;
    attempt_number: number;
    status: DisplayTestOutcome | "in_progress";
    started_at: string;
    completed_at: string | null;
    duration_seconds: number | null;
    result: DisplayTestResult | null;
}

export interface DisplayTestState {
    status: "not_started" | "in_progress" | DisplayTestOutcome;
    attempts: DisplayTestAttempt[];
    latest_result: DisplayTestResult | null;
}

export interface DisplayDiagnostic {
    diagnostic_id: string;
    session_id: string;
    device_id: string;
    status: "in_progress" | "completed";
    overall_status: string | null;
    created_at: string;
    updated_at: string;
    completed_at: string | null;
    current_test_id: string;
    display_metadata: Record<string, unknown>;
    tests: Record<string, DisplayTestState>;
    evaluation?: Record<string, unknown>;
}

export async function createDiagnosticSession(
    deviceId?: string,
    intake?: DiagnosticSessionIntake,
    sessionId?: string,
) {
    const payload = {
        ...(deviceId ? { device_id: deviceId } : {}),
        ...(intake || {}),
        ...(sessionId ? { session_id: sessionId } : {}),
    };
    const response = await api.post(
        "/diagnostic-sessions/",
        payload,
    );

    return response.data;
}

export async function getDiagnosticSession(sessionId: string): Promise<DiagnosticSession> {
    const response = await api.get(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}`,
    );
    return response.data;
}

export async function getDiagnosticSessions(): Promise<DiagnosticSession[]> {
    const response = await api.get("/diagnostic-sessions/");
    return response.data;
}

export async function deleteDiagnosticSession(sessionId: string) {
    await api.delete(`/diagnostic-sessions/${encodeURIComponent(sessionId)}`);
}

export async function updateSessionIntake(
    sessionId: string,
    deviceId: string,
    intake: Record<string, unknown>,
    deviceInventory: Array<Record<string, unknown>>,
) {
    const response = await api.put(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/intake`,
        {
            device_id: deviceId,
            intake_record: intake,
            device_inventory: deviceInventory,
        },
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
    result: {
        outcome: "passed" | "failed" | "warning" | "not_applicable" | "blocked" | "not_run";
        notes: string;
        scan_status: "success" | "no_results" | "unsupported" | "error" | "not_attempted";
        detected_devices: string[];
        technician_decision: "working" | "not_working" | "unable_to_verify" | null;
        evidence: Record<string, unknown>;
    },
) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/manual/${encodeURIComponent(checkId)}`,
        result,
    );
    return response.data;
}

export async function startDisplayDiagnostic(
    sessionId: string,
): Promise<DisplayDiagnostic> {
    const response = await api.post<DisplayDiagnostic>(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/display/start`,
    );
    return response.data;
}

export async function getDisplayDiagnostic(
    sessionId: string,
): Promise<DisplayDiagnostic> {
    const response = await api.get<DisplayDiagnostic>(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/display`,
    );
    return response.data;
}

export async function updateDisplayProgress(
    sessionId: string,
    currentTestId: string,
): Promise<DisplayDiagnostic> {
    const response = await api.put<DisplayDiagnostic>(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/display/progress`,
        { current_test_id: currentTestId },
    );
    return response.data;
}

export async function startDisplayTest(
    sessionId: string,
    testId: string,
    attemptId: string,
): Promise<{ diagnostic: DisplayDiagnostic; attempt: DisplayTestAttempt }> {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/display/tests/${encodeURIComponent(testId)}/start`,
        { attempt_id: attemptId },
    );
    return response.data;
}

export async function recordDisplayTestResult(
    sessionId: string,
    testId: string,
    result: {
        attempt_id: string;
        status: DisplayTestOutcome;
        notes: string;
        defects: Array<{ type: string; location: string; count?: number }>;
    },
): Promise<{ diagnostic: DisplayDiagnostic; result: DisplayTestResult }> {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/display/tests/${encodeURIComponent(testId)}/result`,
        result,
    );
    return response.data;
}

export async function completeDisplayDiagnostic(
    sessionId: string,
): Promise<DisplayDiagnostic> {
    const response = await api.post<DisplayDiagnostic>(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/display/complete`,
    );
    return response.data;
}

export async function completeDiagnosticSession(sessionId: string) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/complete`
    );

    return response.data;
}

export async function finalizeDiagnosticSession(sessionId: string) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/finalize`,
    );
    return response.data;
}

export async function reopenDiagnosticSession(
    sessionId: string,
    authorization: { actor_label: string; credential: string },
) {
    const response = await api.post(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/reopen`,
        authorization,
    );
    return response.data;
}
