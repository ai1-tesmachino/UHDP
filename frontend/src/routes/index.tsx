import {
    Routes,
    Route,
    Link,
} from "react-router-dom";

import Dashboard from "../pages/Dashboard";
import DeviceDiscovery from "../pages/DeviceDiscovery";
import DiagnosticSelection from "../pages/DiagnosticSelection";
import Execution from "../pages/Execution";
import Results from "../pages/Results";
import ReportViewer from "../pages/ReportViewer";
import DiagnosticJobs from "../pages/DiagnosticJobs";
import Capabilities from "../pages/Capabilities";
import StationSetup from "../pages/StationSetup";
import TestProfiles from "../pages/TestProfiles";
import Analytics from "../pages/Analytics";
import QaReview from "../pages/QaReview";
import StoragePerformance from "../pages/StoragePerformance";
import Photos from "../pages/Photos";
import ActiveQc from "../pages/ActiveQc";
import QcHistory from "../pages/QcHistory";
import Reports from "../pages/Reports";

export default function AppRoutes() {
    return (
        <Routes>
            <Route path="/setup" element={<StationSetup />} />
            <Route
                path="/"
                element={<Dashboard />}
            />

            <Route
                path="/devices"
                element={<DeviceDiscovery />}
            />

            <Route
                path="/test-profiles"
                element={<TestProfiles />}
            />

            <Route
                path="/diagnostics"
                element={<DiagnosticSelection />}
            />

            <Route
                path="/execution"
                element={<Execution />}
            />

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
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/storage-performance" element={<StoragePerformance />} />
            <Route path="/active-qc" element={<ActiveQc />} />
            <Route path="/history" element={<QcHistory />} />
            <Route path="/reports" element={<Reports />} />

            <Route
                path="/diagnostic-jobs"
                element={<DiagnosticJobs />}
            />

            <Route
                path="/stress-testing"
                element={<DiagnosticJobs cpuOnly />}
            />

            <Route
                path="/capabilities"
                element={<Capabilities />}
            />

            <Route
                path="*"
                element={<div className="empty-panel"><h1>Page not found</h1><p>This UHDP page does not exist. Use the inspection navigation or return to the dashboard.</p><Link className="button button-primary" to="/">Return to dashboard</Link></div>}
            />
        </Routes>
    );
}