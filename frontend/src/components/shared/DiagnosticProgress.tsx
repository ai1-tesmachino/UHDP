import { Progress } from "@/components/ui/progress";

export function DiagnosticProgress({ value, label = "Workflow progress" }: { value: number; label?: string }) {
    const progress = Math.max(0, Math.min(100, value));
    return (
        <div className="diagnostic-progress">
            <div className="diagnostic-progress-label">
                <span>{label}</span>
                <span>{progress}%</span>
            </div>
            <Progress value={progress} aria-label={`${label}: ${progress}%`} />
        </div>
    );
}
