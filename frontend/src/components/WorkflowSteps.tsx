import { Link, useLocation } from "react-router-dom";

const steps = [
    { label: "Overview", path: "/" },
    { label: "Devices", path: "/devices" },
    { label: "Diagnostics", path: "/diagnostics" },
    { label: "Execution", path: "/execution" },
    { label: "Results", path: "/results" },
    { label: "Report", path: "/report" },
];

export default function WorkflowSteps() {
    const { pathname } = useLocation();
    const activeIndex = Math.max(
        0,
        steps.findIndex((step) =>
            step.path === "/"
                ? pathname === "/"
                : pathname.startsWith(step.path)
        )
    );

    return (
        <nav className="workflow-steps" aria-label="Diagnostic workflow">
            {steps.map((step, index) => {
                const className = [
                    "workflow-step",
                    index < activeIndex ? "complete" : "",
                    index === activeIndex ? "current" : "",
                ]
                    .filter(Boolean)
                    .join(" ");

                return (
                    <Link
                        className={className}
                        key={step.path}
                        to={step.path}
                        aria-current={index === activeIndex ? "step" : undefined}
                    >
                        <span className="workflow-step-number">
                            {index < activeIndex ? "✓" : index + 1}
                        </span>
                        <span>{step.label}</span>
                    </Link>
                );
            })}
        </nav>
    );
}
