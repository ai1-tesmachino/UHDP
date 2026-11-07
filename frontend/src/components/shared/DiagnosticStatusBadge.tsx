import { Badge } from "@/components/ui/badge";

const statusPresentation: Record<string, { label: string; className: string }> = {
    pass: { label: "Passed", className: "status-badge-success" },
    passed: { label: "Passed", className: "status-badge-success" },
    success: { label: "Passed", className: "status-badge-success" },
    ok: { label: "Passed", className: "status-badge-success" },
    healthy: { label: "Healthy", className: "status-badge-success" },
    fail: { label: "Failed", className: "status-badge-destructive" },
    failed: { label: "Failed", className: "status-badge-destructive" },
    error: { label: "Error", className: "status-badge-destructive" },
    defective: { label: "Defective", className: "status-badge-destructive" },
    warning: { label: "Warning", className: "status-badge-warning" },
    attention: { label: "Attention required", className: "status-badge-warning" },
    inconclusive: { label: "Inconclusive", className: "status-badge-neutral" },
    unsupported: { label: "Unsupported", className: "status-badge-neutral" },
    blocked: { label: "Blocked", className: "status-badge-neutral" },
    cancelled: { label: "Cancelled", className: "status-badge-neutral" },
    canceled: { label: "Cancelled", className: "status-badge-neutral" },
    not_applicable: { label: "Not applicable", className: "status-badge-neutral" },
    skipped: { label: "Skipped", className: "status-badge-neutral" },
    in_progress: { label: "In progress", className: "status-badge-information" },
    pending: { label: "Pending", className: "status-badge-neutral" },
    not_tested: { label: "Not tested", className: "status-badge-neutral" },
    unknown: { label: "Unknown", className: "status-badge-neutral" },
    complete: { label: "Completed", className: "status-badge-neutral" },
    completed: { label: "Completed", className: "status-badge-neutral" },
};

export function DiagnosticStatusBadge({ status }: { status: string }) {
    const normalized = status.toLowerCase().replaceAll(" ", "_");
    const presentation = statusPresentation[normalized] || {
        label: status.replaceAll("_", " "),
        className: "status-badge-neutral",
    };

    return <Badge variant="outline" className={presentation.className}>{presentation.label}</Badge>;
}
