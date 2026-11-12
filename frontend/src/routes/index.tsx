import {
    Routes,
    Route,
    Link,
    Navigate,
    useSearchParams,
} from "react-router-dom";

import DeviceInventory from "../pages/Dashboard";
import Dashboard from "../pages/TechnicianDashboard";
import DeviceDiscovery from "../pages/DeviceDiscovery";
import DeviceIdentification from "../pages/DeviceIdentification";
import PhysicalAssessment from "../pages/PhysicalAssessment";
import Results from "../pages/Results";
import ReportViewer from "../pages/ReportViewer";
import StationSetup from "../pages/StationSetup";
import QaReview from "../pages/QaReview";
import Photos from "../pages/Photos";
import ActiveQc from "../pages/ActiveQc";
import QcHistory from "../pages/QcHistory";
import Reports from "../pages/Reports";
import QcInspection from "../pages/QcInspection";
import CosmeticInspection from "../pages/CosmeticInspection";
import FieldRequirements from "../pages/FieldRequirements";
import SessionOverview from "../pages/SessionOverview";
import DisplayDiagnosticPage from "../diagnostics/display/DisplayDiagnosticPage";

function InspectionRoute() {
    const [params] = useSearchParams();
    return params.get("stage") === "cosmetic"
        ? <CosmeticInspection />
        : <QcInspection />;
}

export default function AppRoutes() {
    return (
        <Routes>
            <Route path="/setup" element={<StationSetup />} />
            <Route path="/settings/field-requirements" element={<FieldRequirements />} />
            <Route path="/" element={<Dashboard />} />
            <Route path="/device-identification" element={<DeviceIdentification />} />
            <Route path="/physical-assessment" element={<PhysicalAssessment />} />
            <Route
                path="/hardware-diagnostics"
                element={
                    <main className="empty-panel">
                        <h1>Hardware Diagnostics</h1>
                        <p>The next inspection stage is under development.</p>
                    </main>
                }
            />
            <Route path="/inventory" element={<DeviceInventory />} />
            <Route path="/sessions" element={<SessionOverview />} />

            <Route
                path="/devices"
                element={<DeviceDiscovery />}
            />

            <Route path="/qc" element={<InspectionRoute />} />
            <Route
                path="/diagnostics/display/:sessionId"
                element={<DisplayDiagnosticPage />}
            />
            <Route path="/diagnostics" element={<Navigate to="/qc?stage=functional&standalone=1" replace />} />

            <Route
                path="/results"
                element={<Results />}
            />

            <Route
                path="/report"
                element={<ReportViewer />}
            />

            <Route path="/qa" element={<QaReview />} />
            <Route path="/photos" element={<Photos />} />
            <Route path="/active-qc" element={<ActiveQc />} />
            <Route path="/history" element={<QcHistory />} />
            <Route path="/reports" element={<Reports />} />

            <Route
                path="*"
                element={<div className="empty-panel"><h1>Page not found</h1><p>This UHDP page does not exist. Use the inspection navigation or return to the dashboard.</p><Link className="button button-primary" to="/">Return to dashboard</Link></div>}
            />
        </Routes>
    );
}