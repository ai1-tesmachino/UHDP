import { ReactNode } from "react";

interface Props {
    children: ReactNode;
    required?: boolean;
    className?: string;
}

export default function FieldLabel({ children, required = false, className }: Props) {
    return (
        <label className={className}>
            <span className="field-label-text">
                {children}
                {required && <span className="required-field-mark" aria-label="required"> *</span>}
            </span>
        </label>
    );
}
