import type { ReactNode } from "react";

interface PageHeaderProps {
    title: string;
    description?: string;
    eyebrow?: string;
    actions?: ReactNode;
}

export function PageHeader({ title, description, eyebrow, actions }: PageHeaderProps) {
    return (
        <header className="page-header">
            <div>
                {eyebrow && <span className="eyebrow">{eyebrow}</span>}
                <h1 className="page-title">{title}</h1>
                {description && <p className="page-description">{description}</p>}
            </div>
            {actions && <div className="page-header-actions">{actions}</div>}
        </header>
    );
}
