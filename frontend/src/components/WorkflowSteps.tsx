import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { EvidenceMetadata, getSessionEvidence } from "../api/evidence";
import { useQcSession } from "../session/SessionContext";

const steps = [
    { label: "Intake", path: "devices" },
    { label: "Cosmetic", path: "cosmetic" },
    { label: "Functional", path: "functional" },
    { label: "Photos", path: "photos" },
    { label: "Review", path: "review" },
    { label: "Disposition", path: "disposition" },
    { label: "Report", path: "report" },
];

export default function WorkflowSteps() {
    const location = useLocation();
    const { activeSession } = useQcSession();
    const params = new URLSearchParams(location.search);
    const standalone = params.get("standalone") === "1";
    const sessionId = params.get("new") === "1"
        ? ""
        : params.get("sessionId") || activeSession?.session_id || "";
    const [evidence, setEvidence] = useState<EvidenceMetadata[]>([]);

    useEffect(() => {
        if (location.pathname === "/" || !sessionId) {
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
    }, [location.pathname, sessionId]);

    if (standalone || !sessionId || ["/", "/sessions", "/setup", "/history", "/reports", "/active-qc"].includes(location.pathname)) return null;

    let activeIndex = 0;
    const path = location.pathname;
    if (path === "/devices") {
        activeIndex = 0;
    } else if (path === "/qc") {
        activeIndex = new URLSearchParams(location.search).get("stage") === "cosmetic" ? 1 : 2;
    } else if (path === "/photos") {
        activeIndex = 3;
    } else if (path === "/results") {
        activeIndex = 4;
    } else if (path === "/qa") {
        activeIndex = 5;
    } else if (path === "/report") {
        activeIndex = 6;
    }

    const intake = activeSession?.intake_record || {};
    const manual = activeSession?.manual_results || {};
    const technicianRecord = activeSession?.technician_record || {};
    const cosmeticItems = activeSession?.cosmetic_inspections?.initial?.items || {};
    const cosmeticComplete = Object.values(cosmeticItems).length > 0 &&
        Object.values(cosmeticItems).every((item) =>
            Boolean(item.condition && item.severity && item.technician_confirmed),
        );
    const functionalComplete = Object.entries(manual).some(
        ([key, value]) => !key.endsWith("_cosmetic") && key !== "physical_inspection" && Boolean(value),
    );
    const completed = [
        Boolean(activeSession?.device_id && Object.keys(intake).length),
        cosmeticComplete,
        functionalComplete,
        evidence.length > 0,
        ["checks_complete", "completed"].includes(activeSession?.status || ""),
        Boolean(technicianRecord.final_disposition),
        activeSession?.status === "completed",
    ];
    function stepHref(index: number) {
        const step = steps[index];
        const query = new URLSearchParams({ sessionId });
        if (activeSession?.device_id) query.set("deviceId", activeSession.device_id);
        if (step.path === "devices") return `/devices?${query.toString()}`;
        if (step.path === "cosmetic" || step.path === "functional") {
            query.set("stage", step.path);
            return `/qc?${query.toString()}`;
        }
        if (step.path === "photos") return `/photos?${query.toString()}`;
        if (step.path === "review") return `/results?${query.toString()}`;
        if (step.path === "disposition") return `/qa?${query.toString()}`;
        return `/report?${query.toString()}`;
    }

    return (
        <>
            <nav className="workflow-steps" aria-label="Inspection progress">
                {steps.map((step, index) => (
                    index <= activeIndex ? (
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
                    ) : (
                        <span className="workflow-step locked" key={step.path} aria-disabled="true">
                            <span className="workflow-step-number">{index + 1}</span>
                            <span>{step.label}</span>
                        </span>
                    )
                ))}
            </nav>
        </>
    );
}
