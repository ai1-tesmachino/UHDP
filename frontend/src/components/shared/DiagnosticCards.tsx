import type { ReactNode } from "react";
import { Activity, Check, CircleAlert, CircleHelp, X } from "lucide-react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { DiagnosticStatusBadge } from "./DiagnosticStatusBadge";

export function DiagnosticCategoryCard({ icon, title, description, children }: {
    icon: ReactNode;
    title: string;
    description: string;
    children?: ReactNode;
}) {
    return (
        <Card className="diagnostic-category-card">
            <CardHeader>
                <span className="diagnostic-category-icon" aria-hidden="true">{icon}</span>
                <CardTitle>{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            {children && <CardContent>{children}</CardContent>}
        </Card>
    );
}

export function DiagnosticResultCard({ title, status, summary, children }: {
    title: string;
    status: string;
    summary?: string;
    children?: ReactNode;
}) {
    return (
        <Card>
            <CardHeader className="diagnostic-result-card-header">
                <div>
                    <CardTitle>{title}</CardTitle>
                    {summary && <CardDescription>{summary}</CardDescription>}
                </div>
                <DiagnosticStatusBadge status={status} />
            </CardHeader>
            {children && <CardContent>{children}</CardContent>}
        </Card>
    );
}

const indicatorIcons = {
    pass: Check,
    passed: Check,
    success: Check,
    ok: Check,
    healthy: Check,
    fail: X,
    failed: X,
    error: X,
    defective: X,
    warning: CircleAlert,
    attention: CircleAlert,
    in_progress: Activity,
    pending: CircleHelp,
    not_tested: CircleHelp,
    inconclusive: CircleHelp,
    unsupported: CircleHelp,
    blocked: CircleHelp,
    cancelled: CircleHelp,
    canceled: CircleHelp,
    not_applicable: CircleHelp,
    skipped: CircleHelp,
    complete: CircleHelp,
    completed: CircleHelp,
};

export function TestStatusIndicator({ status }: { status: string }) {
    const key = status.toLowerCase().replaceAll(" ", "_") as keyof typeof indicatorIcons;
    const Icon = indicatorIcons[key] || CircleHelp;
    return (
        <span className={`test-status-indicator status-${key}`}>
            <Icon size={15} aria-hidden="true" />
            <DiagnosticStatusBadge status={status} />
        </span>
    );
}

export function TechnicianAssessmentPanel({ title = "Technician assessment", children }: {
    title?: string;
    children: ReactNode;
}) {
    return (
        <Card>
            <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
            <CardContent>{children}</CardContent>
        </Card>
    );
}
