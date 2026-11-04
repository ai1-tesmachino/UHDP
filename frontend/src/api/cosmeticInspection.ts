import api from "./client";

export type CosmeticCondition =
    | "Excellent"
    | "Good"
    | "Average"
    | "Damaged"
    | "Missing"
    | "Not Applicable";

export type DamageSeverity = "None" | "Minor" | "Moderate" | "Severe";
export type CosmeticInspectionPhase = "initial" | "final";

export interface CosmeticItemRecord {
    name: string;
    areas: CosmeticArea[];
    condition: CosmeticCondition | null;
    severity: DamageSeverity | null;
    damage_description: string;
    damage_location: string;
    notes: string;
    evidence_ids: string[];
    technician_confirmed: boolean;
    custom: boolean;
    model_dependent: boolean;
}

export type CosmeticArea = "A" | "B" | "C" | "D" | "E";

export interface CosmeticInspectionRecord {
    items: Record<string, CosmeticItemRecord>;
    updated_at: string;
}

export type CosmeticInspections = Partial<
    Record<CosmeticInspectionPhase, CosmeticInspectionRecord>
>;

export async function saveCosmeticInspection(
    sessionId: string,
    phase: CosmeticInspectionPhase,
    items: Record<string, CosmeticItemRecord>,
): Promise<CosmeticInspectionRecord> {
    const response = await api.put<{ inspection: CosmeticInspectionRecord }>(
        `/diagnostic-sessions/${encodeURIComponent(sessionId)}/cosmetic-inspection/${phase}`,
        { items },
    );
    return response.data.inspection;
}
