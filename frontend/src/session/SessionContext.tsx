import {
    createContext,
    ReactNode,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from "react";
import { useLocation } from "react-router-dom";

import {
    assetResolutionConfirmed,
    assetResolutionRequestFields,
    createDiagnosticSession,
    DiagnosticSessionIntake,
    getDiagnosticSession,
    DiagnosticSession,
} from "../api/execution";
import type { AssetResolutionSelection } from "../api/execution";

const ACTIVE_SESSION_KEY = "uhdp.active_qc_session_id";
const PENDING_SESSION_KEY = "uhdp.pending_qc_session_id";

interface SessionContextValue {
    activeSession: DiagnosticSession | null;
    activeSessionId: string;
    loading: boolean;
    error: string;
    startSession: (
        assetResolution: AssetResolutionSelection,
        deviceId?: string,
        intake?: DiagnosticSessionIntake,
    ) => Promise<DiagnosticSession>;
    activateSession: (sessionId: string) => Promise<DiagnosticSession>;
    deactivateSession: () => void;
    refreshSession: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

function createSessionId() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }

    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
        const random = Math.floor(Math.random() * 16);
        return (character === "x" ? random : (random & 0x3) | 0x8).toString(16);
    });
}

export function SessionProvider({
    children,
    disabled = false,
}: {
    children: ReactNode;
    disabled?: boolean;
}) {
    const location = useLocation();
    const displaySessionId = location.pathname.startsWith("/diagnostics/display/")
        ? decodeURIComponent(location.pathname.slice("/diagnostics/display/".length))
        : "";
    const routeSessionId =
        new URLSearchParams(location.search).get("sessionId") || displaySessionId;
    const [activeSession, setActiveSession] = useState<DiagnosticSession | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const activateSession = useCallback(async (sessionId: string) => {
        if (disabled) {
            throw new Error("Session actions are disabled in the demo workflow.");
        }
        setLoading(true);
        setError("");
        try {
            const session = await getDiagnosticSession(sessionId);
            localStorage.setItem(ACTIVE_SESSION_KEY, session.session_id);
            localStorage.removeItem(PENDING_SESSION_KEY);
            setActiveSession(session);
            return session;
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "The inspection session could not be loaded.");
            throw loadError;
        } finally {
            setLoading(false);
        }
    }, [disabled]);

    const startSession = useCallback(async (
        assetResolution: AssetResolutionSelection,
        deviceId?: string,
        intake: DiagnosticSessionIntake = {},
    ) => {
        if (disabled) {
            throw new Error("Session actions are disabled in the demo workflow.");
        }
        setLoading(true);
        setError("");
        const sessionId =
            localStorage.getItem(PENDING_SESSION_KEY) || createSessionId();
        if (
            assetResolution.mode === "existing" &&
            !assetResolution.assetId.trim()
        ) {
            setLoading(false);
            throw new Error("Enter an existing asset ID to link to this QC session.");
        }
        localStorage.setItem(PENDING_SESSION_KEY, sessionId);

        try {
            const assetFields = assetResolutionRequestFields(assetResolution);
            const response = await createDiagnosticSession(
                deviceId,
                { ...intake, ...assetFields },
                sessionId,
            );
            if (!assetResolutionConfirmed(response.asset_id, assetResolution)) {
                throw new Error("The backend did not confirm the requested asset identity.");
            }
            const session = await getDiagnosticSession(response.session_id);
            localStorage.setItem(ACTIVE_SESSION_KEY, session.session_id);
            localStorage.removeItem(PENDING_SESSION_KEY);
            setActiveSession(session);
            return session;
        } catch (startError) {
            setError(startError instanceof Error ? startError.message : "A new inspection session could not be created.");
            throw startError;
        } finally {
            setLoading(false);
        }
    }, [disabled]);

    const refreshSession = useCallback(async () => {
        if (disabled) return;
        const sessionId =
            routeSessionId ||
            activeSession?.session_id ||
            localStorage.getItem(ACTIVE_SESSION_KEY);
        if (!sessionId) {
            setActiveSession(null);
            return;
        }
        try {
            const session = await getDiagnosticSession(sessionId);
            setActiveSession(session);
            setError("");
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "The inspection session could not be refreshed.");
            throw loadError;
        }
    }, [activeSession?.session_id, disabled, routeSessionId]);

    const deactivateSession = useCallback(() => {
        localStorage.removeItem(ACTIVE_SESSION_KEY);
        setActiveSession(null);
        setError("");
    }, []);

    useEffect(() => {
        if (disabled) {
            setActiveSession(null);
            setLoading(false);
            setError("");
            return;
        }
        const pendingId = localStorage.getItem(PENDING_SESSION_KEY);
        const activeId = localStorage.getItem(ACTIVE_SESSION_KEY);
        if (pendingId) {
            void activateSession(pendingId)
                .catch(() => setLoading(false));
            return;
        }
        if (activeId) {
            void activateSession(activeId).catch(() => undefined);
            return;
        }
        setLoading(false);
    }, [activateSession, disabled]);

    useEffect(() => {
        if (disabled) return;
        const sessionId = routeSessionId;
        if (sessionId && sessionId !== activeSession?.session_id) {
            void activateSession(sessionId).catch(() => undefined);
        }
    }, [activateSession, activeSession?.session_id, disabled, routeSessionId]);

    useEffect(() => {
        if (disabled || !activeSession?.session_id) return;
        const refresh = () => {
            void refreshSession().catch(() => undefined);
        };
        const timer = window.setInterval(refresh, 5000);
        window.addEventListener("focus", refresh);
        return () => {
            window.clearInterval(timer);
            window.removeEventListener("focus", refresh);
        };
    }, [activeSession?.session_id, disabled, refreshSession]);

    useEffect(() => {
        if (disabled) return;
        const syncActiveSession = (event: StorageEvent) => {
            const routeSessionId = new URLSearchParams(location.search).get("sessionId");
            if (
                !routeSessionId &&
                event.key === ACTIVE_SESSION_KEY &&
                event.newValue &&
                event.newValue !== activeSession?.session_id
            ) {
                void activateSession(event.newValue).catch(() => undefined);
            }
        };
        window.addEventListener("storage", syncActiveSession);
        return () => window.removeEventListener("storage", syncActiveSession);
    }, [activateSession, activeSession?.session_id, disabled, location.search]);

    const value = useMemo(
        () => ({
            activeSession,
            activeSessionId: activeSession?.session_id || "",
            loading,
            error,
            startSession,
            activateSession,
            deactivateSession,
            refreshSession,
        }),
        [activeSession, loading, error, startSession, activateSession, deactivateSession, refreshSession],
    );

    return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useQcSession() {
    const context = useContext(SessionContext);
    if (!context) {
        throw new Error("useQcSession must be used within a SessionProvider.");
    }
    return context;
}
