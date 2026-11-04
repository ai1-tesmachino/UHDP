import { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";
import { Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { TooltipProvider } from "./components/ui/tooltip";

import Layout from "./components/layout/ApplicationLayout";
import AppRoutes from "./routes";
import { SessionProvider } from "./session/SessionContext";
import { getStationProfile } from "./station";
import { ThemeProvider, useTheme } from "./theme/ThemeProvider";

function StationGate({ children }: { children: ReactNode }) {
    const location = useLocation();
    if (!getStationProfile() && location.pathname !== "/setup") {
        return <Navigate to="/setup" replace state={{ from: location.pathname + location.search }} />;
    }
    return children;
}

function Application() {
    const { theme } = useTheme();
    return (
        <BrowserRouter>
            <TooltipProvider>
                <StationGate>
                    <SessionProvider>
                        <Layout>
                            <AppRoutes />
                        </Layout>
                    </SessionProvider>
                </StationGate>
                <Toaster position="top-right" theme={theme} richColors closeButton />
            </TooltipProvider>
        </BrowserRouter>
    );
}

export default function App() {
    return <ThemeProvider><Application /></ThemeProvider>;
}