import type { CosmeticInspections, CosmeticItemRecord } from "../api/cosmeticInspection";
import { getEvidenceUrl } from "../api/evidence";

interface Props {
    inspections: CosmeticInspections;
}

function comparison(initial?: CosmeticItemRecord, current?: CosmeticItemRecord) {
    const rank: Record<string, number> = {
        Missing: 0,
        Damaged: 1,
        Average: 2,
        Good: 3,
        Excellent: 4,
    };
    const initialCondition = initial?.condition;
    const currentCondition = current?.condition;
    if (!initialCondition || !currentCondition || initialCondition === "Not Applicable" || currentCondition === "Not Applicable") return "";
    if (!(initialCondition in rank) || !(currentCondition in rank)) return "";
    if (rank[currentCondition] > rank[initialCondition]) return "Improved";
    if (rank[currentCondition] < rank[initialCondition]) return "Deteriorated";
    const severityRank = { None: 4, Minor: 3, Moderate: 2, Severe: 1 };
    if (initial.severity && current.severity && initial.severity !== current.severity) {
        return severityRank[current.severity] > severityRank[initial.severity]
            ? "Improved"
            : "Deteriorated";
    }
    return "Unchanged";
}

export default function CosmeticAssessmentSummary({ inspections }: Props) {
    const initialItems = inspections.initial?.items || {};
    const finalItems = inspections.final?.items || {};
    const ids = [...new Set([...Object.keys(initialItems), ...Object.keys(finalItems)])];
    if (!ids.length) return null;

    return (
        <section className="results-table-panel cosmetic-report-panel">
            <div className="section-heading">
                <div>
                    <span className="eyebrow">PHYSICAL CONDITION</span>
                    <h2>Cosmetic assessment history</h2>
                </div>
                <span className="section-count">
                    {inspections.initial ? "Initial assessment saved" : "No initial assessment"}
                    {inspections.final ? " · Final verification saved" : ""}
                </span>
            </div>
            <div className="cosmetic-report-list">
                {ids.map((id) => {
                    const initial = initialItems[id];
                    const final = finalItems[id];
                    const name = final?.name || initial?.name || id;
                    const result = comparison(initial, final);
                    return (
                        <article className="cosmetic-report-row" key={id}>
                            <strong>{name}</strong>
                            <div>
                                <span>Initial</span>
                                <b>{initial?.condition || "Not recorded"}</b>
                                {initial?.severity && initial.severity !== "None" && <small>{initial.severity}</small>}
                            </div>
                            <div>
                                <span>Final</span>
                                <b>{final?.condition || "Not verified"}</b>
                                {final?.severity && final.severity !== "None" && <small>{final.severity}</small>}
                                {result && <em className={`cosmetic-comparison-badge is-${result.toLowerCase()}`}>{result}</em>}
                            </div>
                            <p>
                                {final?.damage_description || initial?.damage_description || final?.notes || initial?.notes || "—"}
                                {(final?.damage_location || initial?.damage_location)
                                    ? ` · ${final?.damage_location || initial?.damage_location}`
                                    : ""}
                            </p>
                            <div className="cosmetic-report-photos">
                                {[...(initial?.evidence_ids || []), ...(final?.evidence_ids || [])].map((evidenceId, index) => (
                                    <a href={getEvidenceUrl(evidenceId)} target="_blank" rel="noreferrer" key={evidenceId}>
                                        Photo {index + 1} <span aria-hidden="true">↗</span>
                                    </a>
                                ))}
                            </div>
                        </article>
                    );
                })}
            </div>
        </section>
    );
}
