import { useLocation, useSearchParams } from "react-router-dom";

const steps = ["Device", "Automated checks", "Manual checks", "Review", "Report"];

export default function WorkflowSteps() {
    const { pathname } = useLocation();
    const [params] = useSearchParams();
    let activeIndex = 0;

    if (pathname.startsWith("/test-profiles") || pathname.startsWith("/diagnostics")) {
        activeIndex = 1;
    } else if (pathname.startsWith("/execution")) {
        activeIndex = params.get("mode") === "manual" ? 2 : 1;
    } else if (pathname.startsWith("/results") || pathname.startsWith("/qa")) {
        activeIndex = 3;
    } else if (pathname.startsWith("/report")) {
        activeIndex = 4;
    }

    return (
        <nav className="workflow-steps" aria-label="Inspection progress">
            {steps.map((label, index) => (
                <div
                    className={[
                        "workflow-step",
                        index < activeIndex ? "complete" : "",
                        index === activeIndex ? "current" : "",
                    ].filter(Boolean).join(" ")}
                    key={label}
                    aria-current={index === activeIndex ? "step" : undefined}
                >
                    <span className="workflow-step-number">
                        {index < activeIndex ? "✓" : index + 1}
                    </span>
                    <span>{label}</span>
                </div>
            ))}
        </nav>
    );
}
