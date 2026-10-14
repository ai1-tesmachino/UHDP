import { useEffect, useState } from "react";

import { getReport, getReports, RecentReport } from "../api/reports";
import { getStationProfile } from "../station";

interface CheckRecord {
    status?: string;
    [key: string]: unknown;
}

function statusOf(value: unknown): string {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
        return "";
    }
    return String((value as CheckRecord).status || "").toLowerCase();
}

export default function Analytics() {
    const [reports, setReports] = useState<RecentReport[]>([]);
    const [failedChecks, setFailedChecks] = useState<Record<string, number>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const station = getStationProfile();

    useEffect(() => {
        let active = true;
        async function load() {
            try {
                const loaded = await getReports();
                const sorted = [...loaded].sort(
                    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
                );
                const stationReports = sorted.filter((report) => report.station_id === station?.station_id);
                const recent = stationReports.slice(0, 25);
                const details = await Promise.allSettled(
                    recent.map((report) => getReport(report.session_id)),
                );
                const failures: Record<string, number> = {};
                for (const detail of details) {
                    if (detail.status !== "fulfilled") {
                        continue;
                    }
                    const data = detail.value?.data;
                    if (typeof data !== "object" || data === null) {
                        continue;
                    }
                    for (const [name, value] of Object.entries(data as Record<string, unknown>)) {
                        if (statusOf(value) === "failed" || statusOf(value) === "error") {
                            const component = name.replace(/_result$/, "").replaceAll("_", " ");
                            failures[component] = (failures[component] || 0) + 1;
                        } else if (name === "manual_checks" && typeof value === "object" && value !== null) {
                            for (const [checkId, manualValue] of Object.entries(value as Record<string, unknown>)) {
                                if (statusOf(manualValue) === "failed" || statusOf(manualValue) === "error") {
                                    const component = `manual · ${checkId.replaceAll("_", " ")}`;
                                    failures[component] = (failures[component] || 0) + 1;
                                }
                            }
                        }
                    }
                }
                if (active) {
                    setReports(stationReports);
                    setFailedChecks(failures);
                }
            } catch (loadError) {
                if (active) {
                    setError(loadError instanceof Error ? loadError.message : "Production reports could not be loaded.");
                }
            } finally {
                if (active) {
                    setLoading(false);
                }
            }
        }
        void load();
        return () => {
            active = false;
        };
    }, [station?.station_id]);

    const outcomes = reports.map((report) => report.status.toLowerCase());
    const passed = outcomes.filter((status) => status === "passed" || status === "pass").length;
    const failed = outcomes.filter((status) => status === "failed" || status === "fail" || status === "error").length;
    const passRate = passed + failed > 0 ? Math.round((passed / (passed + failed)) * 100) : null;
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
    const lastWeek = reports.filter((report) => new Date(report.created_at).getTime() >= cutoff).length;
    const repeatDevices = new Set(
        reports
            .map((report) => report.device_id)
            .filter((deviceId) => reports.filter((report) => report.device_id === deviceId).length > 1),
    ).size;
    const retestCount = reports.filter((report) => report.retest_of_session_id).length;

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">PRODUCTION OPERATIONS</span>
                    <h1 className="page-title">Station analytics</h1>
                    <p className="page-description">Station {station?.station_id || "unknown"} · Metrics are derived from reports tagged to this station; failure distribution samples its latest 25 reports. Incomplete or unclassified statuses are not counted as passes.</p>
                </div>
            </div>
            {error && <div className="error-box">{error}</div>}
            {loading ? <div className="loading-panel">Loading saved inspections…</div> : (
                <>
                    <section className="analytics-grid">
                        <article className="analytics-card"><span>Saved inspections</span><strong>{reports.length}</strong><small>Available in the report repository</small></article>
                        <article className="analytics-card"><span>Inspections · 7 days</span><strong>{lastWeek}</strong><small>Based on backend report timestamps</small></article>
                        <article className="analytics-card"><span>Pass rate</span><strong>{passRate === null ? "—" : `${passRate}%`}</strong><small>{passed + failed} reports with a pass/fail outcome</small></article>
                        <article className="analytics-card"><span>Repeat-inspected devices</span><strong>{repeatDevices}</strong><small>Distinct device IDs with multiple saved reports</small></article>
                        <article className="analytics-card"><span>Retest sessions</span><strong>{retestCount}</strong><small>Reports linked to an earlier session</small></article>
                    </section>
                    <section className="results-table-panel">
                        <div className="section-heading"><div><span className="eyebrow">FAILURE DISTRIBUTION</span><h2>Failed checks across the latest 25 reports</h2></div></div>
                        {Object.keys(failedChecks).length === 0 ? (
                            <p className="empty-state">{reports.length ? "No failed diagnostic check records were returned in the sampled reports." : "No saved reports are available yet."}</p>
                        ) : (
                            <div className="failure-list">
                                {Object.entries(failedChecks).sort((a, b) => b[1] - a[1]).map(([name, count]) => (
                                    <div className="failure-row" key={name}><span>{name}</span><strong>{count}</strong></div>
                                ))}
                            </div>
                        )}
                    </section>
                </>
            )}
        </div>
    );
}
