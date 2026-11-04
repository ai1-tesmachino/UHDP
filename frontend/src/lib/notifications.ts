import { toast } from "sonner";

type NotificationKind = "success" | "error" | "warning" | "info";

function notify(kind: NotificationKind, message: string, id?: string) {
    const options = { id: id || `uhdp-${kind}-${message}` };
    switch (kind) {
        case "success":
            return toast.success(message, options);
        case "error":
            return toast.error(message, options);
        case "warning":
            return toast.warning(message, options);
        case "info":
            return toast.info(message, options);
    }
}

export const notifications = {
    success: (message: string, id?: string) => notify("success", message, id),
    error: (message: string, id?: string) => notify("error", message, id),
    warning: (message: string, id?: string) => notify("warning", message, id),
    info: (message: string, id?: string) => notify("info", message, id),
};
