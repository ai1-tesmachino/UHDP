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
    createDiagnosticSession,
    getDiagnosticSession,
    DiagnosticSession,
} from "../api/execution";

const ACTIVE_SESSION_KEY = "uhdp.active_qc_session_id";
const PENDING_SESSION_KEY = "uhdp.pending_qc_session_id";

interface SessionContextValue {
    activeSession: DiagnosticSession | null;
    activeSessionId: string;
    loading: boolean;
    error: string;
    startSession: () => Promise<DiagnosticSession>;
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

export function SessionProvider({ children }: { children: ReactNode }) {
    const location = useLocation();
    const [activeSession, setActiveSession] = useState<DiagnosticSession | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const activateSession = useCallback(async (sessionId: string) => {
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
    }, []);

    const startSession = useCallback(async () => {
        setLoading(true);
        setError("");
        const sessionId =
            localStorage.getItem(PENDING_SESSION_KEY) || createSessionId();
        localStorage.setItem(PENDING_SESSION_KEY, sessionId);

        try {
            const response = await createDiagnosticSession(undefined, undefined, sessionId);
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
    }, []);

    const refreshSession = useCallback(async () => {
        const sessionId =
            new URLSearchParams(location.search).get("sessionId") ||
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
    }, [activeSession?.session_id, location.search]);

    const deactivateSession = useCallback(() => {
        localStorage.removeItem(ACTIVE_SESSION_KEY);
        setActiveSession(null);
        setError("");
    }, []);

    useEffect(() => {
        const pendingId = localStorage.getItem(PENDING_SESSION_KEY);
        const activeId = localStorage.getItem(ACTIVE_SESSION_KEY);
        if (pendingId) {
            void createDiagnosticSession(undefined, undefined, pendingId)
                .then((response) => activateSession(response.session_id))
                .catch((loadError: unknown) => {
                    setError(loadError instanceof Error ? loadError.message : "The pending inspection session could not be resumed.");
                    setLoading(false);
                });
            return;
        }
        if (activeId) {
            void activateSession(activeId).catch(() => undefined);
            return;
        }
        setLoading(false);
    }, [activateSession]);

    useEffect(() => {
        const sessionId = new URLSearchParams(location.search).get("sessionId");
        if (sessionId && sessionId !== activeSession?.session_id) {
            void activateSession(sessionId).catch(() => undefined);
        }
    }, [activateSession, activeSession?.session_id, location.search]);

    useEffect(() => {
        if (!activeSession?.session_id) return;
        const refresh = () => {
            void refreshSession().catch(() => undefined);
        };
        const timer = window.setInterval(refresh, 5000);
        window.addEventListener("focus", refresh);
        return () => {
            window.clearInterval(timer);
            window.removeEventListener("focus", refresh);
        };
    }, [activeSession?.session_id, refreshSession]);

    useEffect(() => {
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
    }, [activateSession, activeSession?.session_id, location.search]);

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
