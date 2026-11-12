import "./inspection-progress.css";

const stages = [
    "Device Identification",
    "Physical Assessment",
    "Hardware Diagnostics",
    "Technician Checks",
    "Review Results",
    "Final Evaluation",
    "Inspection Report",
];

export default function InspectionProgress({
    activeStage,
    deviceConfirmed,
    physicalAssessmentComplete,
    diagnosticsComplete,
    technicianChecksComplete = false,
}: {
    activeStage: number;
    deviceConfirmed: boolean;
    physicalAssessmentComplete: boolean;
    diagnosticsComplete: boolean;
    technicianChecksComplete?: boolean;
}) {
    return (
        <nav className="inspection-progress-panel" aria-label="Inspection progress">
            <ol className="inspection-progress">
                {stages.map((stage, index) => {
                    const isCurrent = index === activeStage;
                    const isComplete =
                        (index === 0 && deviceConfirmed) ||
                        (index === 1 && physicalAssessmentComplete) ||
                        (index === 2 && diagnosticsComplete) ||
                        (index === 3 && technicianChecksComplete);
                    return (
                        <li
                            className={[
                                "inspection-progress-step",
                                isCurrent ? "is-current" : "",
                                isComplete ? "is-complete" : "",
                            ].filter(Boolean).join(" ")}
                            key={stage}
                            aria-current={isCurrent ? "step" : undefined}
                            aria-disabled={index > activeStage ? "true" : undefined}
                        >
                            <span className="inspection-progress-number">
                                {isComplete ? "✓" : index + 1}
                            </span>
                            <span className="inspection-progress-label">{stage}</span>
                        </li>
                    );
                })}
            </ol>
        </nav>
    );
}
