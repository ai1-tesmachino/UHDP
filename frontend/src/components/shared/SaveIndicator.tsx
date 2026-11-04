import { Check, CircleAlert, LoaderCircle } from "lucide-react";

export function SaveIndicator({ state, savedAt }: {
    state: "saved" | "saving" | "error" | "unsaved";
    savedAt?: string | null;
}) {
    const content = {
        saved: { icon: Check, text: savedAt ? `Saved ${new Date(savedAt).toLocaleTimeString()}` : "Saved" },
        saving: { icon: LoaderCircle, text: "Saving" },
        error: { icon: CircleAlert, text: "Save failed" },
        unsaved: { icon: CircleAlert, text: "Unsaved changes" },
    }[state];
    const Icon = content.icon;

    return (
        <span className={`save-indicator save-indicator-${state}`} role="status">
            <Icon aria-hidden="true" size={14} className={state === "saving" ? "animate-spin" : undefined} />
            {content.text}
        </span>
    );
}
