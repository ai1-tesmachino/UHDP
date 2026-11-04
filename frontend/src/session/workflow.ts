import { DiagnosticSession } from "../api/execution";

const RESUME_PATH_PREFIX = "uhdp.qc_session_path.";
const WORKFLOW_PATHS = new Set([
    "/devices",
    "/qc",
    "/photos",
    "/results",
    "/qa",
    "/report",
]);

export function rememberQcPath(sessionId: string, pathname: string, search: string, hash: string) {
    if (!WORKFLOW_PATHS.has(pathname)) return;

    const params = new URLSearchParams(search);
    params.set("sessionId", sessionId);
    const query = params.toString();
    localStorage.setItem(
        `${RESUME_PATH_PREFIX}${sessionId}`,
        `${pathname}${query ? `?${query}` : ""}${hash}`,
    );
}

export function getQcResumePath(
    sessionId: string,
    status?: string,
    deviceId?: string | null,
) {
    const savedPath = localStorage.getItem(`${RESUME_PATH_PREFIX}${sessionId}`);
    if (savedPath?.startsWith("/") && !savedPath.startsWith("//")) {
        const url = new URL(savedPath, window.location.origin);
        if (WORKFLOW_PATHS.has(url.pathname)) {
            url.searchParams.set("sessionId", sessionId);
            return `${url.pathname}${url.search}${url.hash}`;
        }
    }

    const params = new URLSearchParams({ sessionId });
    if (deviceId) params.set("deviceId", deviceId);
    if (["complete", "completed"].includes((status || "").toLowerCase())) {
        return `/report?${params.toString()}`;
    }
    return `/devices?${params.toString()}`;
}

export function isCompletedSession(session: Pick<DiagnosticSession, "status">) {
    return ["complete", "completed"].includes(session.status.toLowerCase());
}

export function getSessionDeviceName(session: DiagnosticSession) {
    const inventory = session.device_inventory || [];
    const device = inventory.find((item) => item.device_id === session.device_id);
    const name = device?.name;
    return typeof name === "string" && name.trim()
        ? name
        : session.device_id || "Device not identified";
}

export function getSessionSerialNumber(session: DiagnosticSession) {
    const inventory = session.device_inventory || [];
    const device = inventory.find((item) => item.device_id === session.device_id);
    const properties = device?.properties;
    if (!properties || typeof properties !== "object" || Array.isArray(properties)) return "Not recorded";

    const propertyRecord = properties as Record<string, unknown>;
    for (const key of ["serial_number", "serial", "SerialNumber"]) {
        const value = propertyRecord[key];
        if (typeof value === "string" && value.trim()) return value;
    }
    return "Not recorded";
}
