import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { EvidenceMetadata, getSessionEvidence } from "../api/evidence";
import { useQcSession } from "../session/SessionContext";

const steps = [
    { label: "Device", path: "devices" },
    { label: "Pre-QC", path: "intake" },
    { label: "Cosmetic", path: "cosmetic" },
    { label: "Functional", path: "functional" },
    { label: "Performance", path: "performance" },
    { label: "Photos", path: "photos" },
    { label: "Review", path: "review" },
    { label: "Disposition", path: "disposition" },
    { label: "Report", path: "report" },
];

export default function WorkflowSteps() {
    const location = useLocation();
    const { activeSession } = useQcSession();
    const params = new URLSearchParams(location.search);
    const sessionId = params.get("new") === "1"
        ? ""
        : params.get("sessionId") || activeSession?.session_id || "";
    const [evidence, setEvidence] = useState<EvidenceMetadata[]>([]);

    useEffect(() => {
        if (!sessionId) {
            setEvidence([]);
            return;
        }
        let active = true;
        getSessionEvidence(sessionId)
            .then((items) => {
                if (active) setEvidence(items);
            })
            .catch(() => {
                if (active) setEvidence([]);
            });
        return () => {
            active = false;
        };
    }, [sessionId]);

    if (
        !sessionId ||
        ["/", "/setup", "/analytics", "/capabilities", "/history", "/reports", "/active-qc"].includes(location.pathname)
    ) return null;

    let activeIndex = 0;
    const path = location.pathname;
    if (path === "/devices") {
        activeIndex = location.hash === "#intake" ? 1 : 0;
    } else if (path === "/test-profiles") {
        activeIndex = 3;
    } else if (path === "/diagnostics") {
        activeIndex = new URLSearchParams(location.search).get("category") === "cosmetic" ? 2 : 3;
    } else if (path === "/execution") {
        activeIndex = new URLSearchParams(location.search).get("category") === "cosmetic" ? 2 : 3;
    } else if (path === "/diagnostic-jobs" || path === "/stress-testing" || path === "/storage-performance") {
        activeIndex = 4;
    } else if (path === "/photos") {
        activeIndex = 5;
    } else if (path === "/results") {
        activeIndex = 6;
    } else if (path === "/qa") {
        activeIndex = 7;
    } else if (path === "/report") {
        activeIndex = 8;
    }

    const intake = activeSession?.intake_record || {};
    const manual = activeSession?.manual_results || {};
    const testResults = activeSession?.test_results || {};
    const performance = activeSession?.performance_results || {};
    const technicianRecord = activeSession?.technician_record || {};
    const completed = [
        Boolean(activeSession?.device_id),
        Boolean(activeSession?.device_id && Object.keys(intake).length),
        Object.keys(manual).some((key) => key === "physical_inspection" || key.endsWith("_cosmetic")),
        Object.keys(testResults).some((key) => key !== "physical_inspection" && !key.endsWith("_cosmetic")) ||
            Object.keys(manual).some((key) => key !== "physical_inspection" && !key.endsWith("_cosmetic")),
        Object.keys(performance).length > 0,
        evidence.length > 0,
        ["checks_complete", "completed"].includes(activeSession?.status || ""),
        Boolean(technicianRecord.final_disposition),
        activeSession?.status === "completed",
    ];
    if (path === "/") {
        const nextStep = completed.findIndex((isComplete) => !isComplete);
        activeIndex = nextStep === -1 ? steps.length - 1 : nextStep;
    }

    function stepHref(index: number) {
        const step = steps[index];
        const query = new URLSearchParams({ sessionId });
        if (activeSession?.device_id) query.set("deviceId", activeSession.device_id);
        if (step.path === "cosmetic") {
            query.set("mode", "manual");
            query.set("category", "cosmetic");
        }
        if (step.path === "intake") return `/devices?${query.toString()}#intake`;
        if (step.path === "devices") return `/devices?${query.toString()}`;
        if (step.path === "cosmetic" || step.path === "functional") return `/diagnostics?${query.toString()}`;
        if (step.path === "performance") return `/diagnostic-jobs?${query.toString()}`;
        if (step.path === "photos") return `/photos?${query.toString()}`;
        if (step.path === "review") return `/results?${query.toString()}`;
        if (step.path === "disposition") return `/qa?${query.toString()}`;
        return `/report?${query.toString()}`;
    }

    return (
        <>
            <nav className="workflow-steps" aria-label="Inspection progress">
                {steps.map((step, index) => (
                    <Link
                        className={[
                            "workflow-step",
                            completed[index] ? "complete" : "",
                            index === activeIndex ? "current" : "",
                        ].filter(Boolean).join(" ")}
                        key={step.path}
                        to={stepHref(index)}
                        aria-current={index === activeIndex ? "step" : undefined}
                    >
                        <span className="workflow-step-number">{completed[index] ? "✓" : index + 1}</span>
                        <span>{step.label}</span>
                    </Link>
                ))}
            </nav>
            <div className="workflow-step-actions">
                <Link
                    className="button button-secondary"
                    to={stepHref(Math.max(0, activeIndex - 1))}
                    aria-disabled={activeIndex === 0}
                    onClick={(event) => {
                        if (activeIndex === 0) event.preventDefault();
                    }}
                >
                    ← Previous
                </Link>
                <span>Step {activeIndex + 1} of {steps.length} · {steps[activeIndex].label}</span>
                <Link
                    className="button button-primary"
                    to={stepHref(Math.min(steps.length - 1, activeIndex + 1))}
                    aria-disabled={activeIndex === steps.length - 1}
                    onClick={(event) => {
                        if (activeIndex === steps.length - 1) event.preventDefault();
                    }}
                >
                    Next →
                </Link>
            </div>
        </>
    );
}
