import {
    Routes,
    Route,
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
            <Route path="/analytics" element={<Analytics />} />

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
                element={<Dashboard />}
            />
        </Routes>
    );
}