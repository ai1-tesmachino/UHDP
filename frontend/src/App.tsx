import { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";
import { Navigate, useLocation } from "react-router-dom";

import Layout from "./components/Layout";
import AppRoutes from "./routes";
import { getStationProfile } from "./station";

function StationGate({ children }: { children: ReactNode }) {
    const location = useLocation();
    if (!getStationProfile() && location.pathname !== "/setup") {
        return <Navigate to="/setup" replace state={{ from: location.pathname + location.search }} />;
    }
    return children;
}

export default function App() {
    return (
        <BrowserRouter>
            <StationGate>
                <Layout>
                    <AppRoutes />
                </Layout>
            </StationGate>
        </BrowserRouter>
    );
}