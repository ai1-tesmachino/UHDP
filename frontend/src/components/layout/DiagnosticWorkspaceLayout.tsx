import type { ReactNode } from "react";
import { ArrowLeft, Maximize, Minimize } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function DiagnosticWorkspaceLayout({ title, backHref, navigation, instructions, children, fullscreen = false, onToggleFullscreen }: {
    title: string;
    backHref: string;
    navigation?: ReactNode;
    instructions?: ReactNode;
    children: ReactNode;
    fullscreen?: boolean;
    onToggleFullscreen?: () => void;
}) {
    return (
        <main className="diagnostic-workspace-layout">
            <header className="diagnostic-workspace-header">
                <Button variant="ghost" size="sm" asChild>
                    <Link to={backHref}><ArrowLeft size={16} aria-hidden="true" /> Back to QC</Link>
                </Button>
                <h1>{title}</h1>
                {onToggleFullscreen && (
                    <Button variant="outline" size="sm" type="button" onClick={onToggleFullscreen}>
                        {fullscreen ? <Minimize size={16} aria-hidden="true" /> : <Maximize size={16} aria-hidden="true" />}
                        {fullscreen ? "Exit fullscreen" : "Fullscreen"}
                    </Button>
                )}
            </header>
            <div className="diagnostic-workspace-body">
                {navigation && <aside className="diagnostic-workspace-navigation" aria-label="Diagnostic test navigation">{navigation}</aside>}
                <section className="diagnostic-workspace-stage" aria-label="Diagnostic workspace">{children}</section>
                {instructions && <aside className="diagnostic-workspace-instructions" aria-label="Technician instructions">{instructions}</aside>}
            </div>
        </main>
    );
}
