import { ReactNode } from "react";
import { BrowserRouter, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { TooltipProvider } from "./components/ui/tooltip";

import Layout from "./components/layout/ApplicationLayout";
import AppRoutes from "./routes";
import { SessionProvider } from "./session/SessionContext";
import { getStationProfile } from "./station";
import { ThemeProvider, useTheme } from "./theme/ThemeProvider";
import { DemoInspectionProvider } from "./demo/DemoInspectionContext";
import { demoWorkflowRoutes } from "./demo/demoWorkflowRoutes";

function StationGate({ children }: { children: ReactNode }) {
    const location = useLocation();
    if (
        location.pathname !== "/" &&
        !getStationProfile() &&
        location.pathname !== "/setup"
    ) {
        return <Navigate to="/setup" replace state={{ from: location.pathname + location.search }} />;
    }
    return children;
}

function ApplicationRoutes() {
    const location = useLocation();
    const isDemoWorkflow = demoWorkflowRoutes.has(location.pathname);
    const application = (
        <SessionProvider disabled={isDemoWorkflow}>
            <Layout>
                <AppRoutes />
            </Layout>
        </SessionProvider>
    );

    return isDemoWorkflow ? application : <StationGate>{application}</StationGate>;
}

function Application() {
    const { theme } = useTheme();
    return (
        <BrowserRouter>
            <TooltipProvider>
                <DemoInspectionProvider>
                    <ApplicationRoutes />
                </DemoInspectionProvider>
                <Toaster position="top-right" theme={theme} richColors closeButton />
            </TooltipProvider>
        </BrowserRouter>
    );
}

export default function App() {
    return <ThemeProvider><Application /></ThemeProvider>;
}