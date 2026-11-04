import { Badge } from "@/components/ui/badge";

type DiagnosticStatus = "passed" | "healthy" | "failed" | "error" | "defective" | "warning" | "attention" |
    "in_progress" | "pending" | "not_tested" | "unsupported" | "unknown" | "complete" | "completed";

const statusPresentation: Record<DiagnosticStatus, { label: string; className: string }> = {
    passed: { label: "Passed", className: "status-badge-success" },
    healthy: { label: "Healthy", className: "status-badge-success" },
    failed: { label: "Failed", className: "status-badge-destructive" },
    error: { label: "Error", className: "status-badge-destructive" },
    defective: { label: "Defective", className: "status-badge-destructive" },
    warning: { label: "Warning", className: "status-badge-warning" },
    attention: { label: "Attention required", className: "status-badge-warning" },
    in_progress: { label: "In progress", className: "status-badge-information" },
    pending: { label: "Pending", className: "status-badge-neutral" },
    not_tested: { label: "Not tested", className: "status-badge-neutral" },
    unsupported: { label: "Unsupported", className: "status-badge-neutral" },
    unknown: { label: "Unknown", className: "status-badge-neutral" },
    complete: { label: "Completed", className: "status-badge-success" },
    completed: { label: "Completed", className: "status-badge-success" },
};

export function DiagnosticStatusBadge({ status }: { status: string }) {
    const normalized = status.toLowerCase().replaceAll(" ", "_") as DiagnosticStatus;
    const presentation = statusPresentation[normalized] || {
        label: status.replaceAll("_", " "),
        className: "status-badge-neutral",
    };

    return <Badge variant="outline" className={presentation.className}>{presentation.label}</Badge>;
}
