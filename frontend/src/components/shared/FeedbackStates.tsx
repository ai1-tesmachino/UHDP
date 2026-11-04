import { AlertCircle, Info, PackageOpen } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function EmptyState({ title, description, action }: {
    title: string;
    description?: string;
    action?: ReactNode;
}) {
    return (
        <div className="feedback-state" role="status">
            <PackageOpen aria-hidden="true" size={20} />
            <strong>{title}</strong>
            {description && <p>{description}</p>}
            {action}
        </div>
    );
}

export function ErrorState({ title = "Something went wrong", description, onRetry }: {
    title?: string;
    description: string;
    onRetry?: () => void;
}) {
    return (
        <div className="feedback-state feedback-state-error" role="alert">
            <AlertCircle aria-hidden="true" size={20} />
            <strong>{title}</strong>
            <p>{description}</p>
            {onRetry && <Button variant="outline" size="sm" onClick={onRetry}>Try again</Button>}
        </div>
    );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
    return (
        <div className="loading-state" role="status" aria-label={label}>
            <Info aria-hidden="true" size={16} />
            <Skeleton className="h-4 w-40" />
            <span className="sr-only">{label}</span>
        </div>
    );
}
