import { ArrowRight, Cpu, FileText, HardDrive, MemoryStick, Monitor, Thermometer } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { notifications } from "../lib/notifications";
import { demoDashboard, getDemoReportCount, getRecentDemoReports } from "../demo/demoDashboard";
import { getTotalInstalledRamGb, getTotalInstalledStorageGb } from "../demo/demoDevice";
import { demoSensors } from "../demo/demoSensors";
import type { DemoReport } from "../demo/demoReports";
import "./dashboard.css";

const device = demoDashboard.device;
const reportCount = getDemoReportCount(demoDashboard.reports);
const recentReports = getRecentDemoReports(demoDashboard.reports);
const totalRamGb = getTotalInstalledRamGb(device);
const totalStorageGb = getTotalInstalledStorageGb(device);

function formatInspectionDate(date: string) {
    return new Intl.DateTimeFormat("en", {
        dateStyle: "medium",
        timeZone: "UTC",
    }).format(new Date(`${date}T12:00:00Z`));
}

function formatOptional(value: string | number | null | undefined, suffix = "") {
    return value === null || value === undefined || value === "" ? "Not Available" : `${value}${suffix}`;
}

function reportResultLabel(result: DemoReport["result"]) {
    return result === "passed" ? "Passed" : "Issues found";
}

function reportResultClass(result: DemoReport["result"]) {
    return result === "passed" ? "is-success" : "is-warning";
}

function SensorChart({ name, unit, readings }: { name: string; unit: string; readings: number[] }) {
    const min = Math.min(...readings);
    const max = Math.max(...readings);
    const range = max - min || 1;
    const points = readings.map((reading, index) => {
        const x = (index / Math.max(readings.length - 1, 1)) * 232 + 4;
        const y = 52 - ((reading - min) / range) * 40;
        return `${x},${y}`;
    }).join(" ");

    return (
        <svg
            className="demo-sensor-chart"
            viewBox="0 0 240 60"
            role="img"
            aria-label={`Demo sample readings for ${name}, ending at ${readings[readings.length - 1]} ${unit}`}
        >
            <line x1="4" y1="53" x2="236" y2="53" className="demo-sensor-chart-axis" />
            <polyline points={points} className="demo-sensor-chart-line" />
        </svg>
    );
}

export default function TechnicianDashboard() {
    const navigate = useNavigate();

    function showDevelopmentNotice(message: string) {
        notifications.info(message);
    }

    return (
        <main className="demo-dashboard page-flow" aria-labelledby="dashboard-title">
            <section className="demo-welcome" aria-labelledby="dashboard-title">
                <div>
                    <span className="eyebrow">DEMO MODE</span>
                    <h1 className="page-title" id="dashboard-title">UHDP Hardware Diagnostics</h1>
                    <p className="page-description">Hardware inspection and quality assessment.</p>
                </div>
                <button
                    className="button button-primary demo-start-button"
                    type="button"
                    onClick={() => navigate("/device-identification")}
                >
                    START DEVICE INSPECTION
                    <ArrowRight size={17} aria-hidden="true" />
                </button>
            </section>

            <section className="demo-device-panel" aria-labelledby="current-device-title">
                <div className="demo-section-heading">
                    <div className="demo-section-title">
                        <HardDrive size={19} aria-hidden="true" />
                        <h2 id="current-device-title">Current Device</h2>
                    </div>
                    <span className="demo-data-label">DEMO DATA · NOT DETECTED</span>
                </div>
                <dl className="demo-device-grid">
                    <div><dt>Manufacturer</dt><dd>{device.manufacturer}</dd></div>
                    <div><dt>Model</dt><dd>{device.model}</dd></div>
                    <div><dt>Processor model</dt><dd>{device.processor.manufacturer} {device.processor.model}</dd></div>
                    <div><dt>Total installed RAM</dt><dd>{totalRamGb} GB</dd></div>
                    <div><dt>Total installed storage</dt><dd>{totalStorageGb} GB</dd></div>
                    <div><dt>Graphics adapter</dt><dd>{device.graphicsAdapter}</dd></div>
                    <div><dt>Screen size</dt><dd>{formatOptional(device.display.screenSizeInches, " in")}</dd></div>
                    <div><dt>Display resolution</dt><dd>{formatOptional(device.display.resolution)}</dd></div>
                </dl>
            </section>

            <section aria-labelledby="hardware-information-title">
                <div className="demo-section-heading">
                    <div className="demo-section-title">
                        <Cpu size={19} aria-hidden="true" />
                        <h2 id="hardware-information-title">Hardware Information</h2>
                    </div>
                    <span className="demo-data-label">All values are sample data</span>
                </div>
                <div className="demo-hardware-grid">
                    <article className="demo-hardware-card demo-hardware-card--third">
                        <div className="demo-card-title"><Cpu size={17} aria-hidden="true" /><h3>Processor</h3></div>
                        <dl className="demo-detail-grid">
                            <div><dt>Manufacturer</dt><dd>{device.processor.manufacturer}</dd></div>
                            <div><dt>CPU model</dt><dd>{device.processor.model}</dd></div>
                            <div><dt>Physical cores</dt><dd>{device.processor.physicalCores}</dd></div>
                            <div><dt>Logical threads</dt><dd>{device.processor.logicalThreads}</dd></div>
                            <div><dt>Base frequency</dt><dd>{formatOptional(device.processor.baseFrequencyGhz, " GHz")}</dd></div>
                            <div><dt>Maximum frequency</dt><dd>{formatOptional(device.processor.maxFrequencyGhz, " GHz")}</dd></div>
                        </dl>
                    </article>

                    <article className="demo-hardware-card demo-hardware-card--third">
                        <div className="demo-card-title"><MemoryStick size={17} aria-hidden="true" /><h3>Memory</h3></div>
                        <div className="demo-hardware-total"><span>Total installed RAM</span><strong>{totalRamGb} GB</strong></div>
                        <div className="demo-module-list">
                            {device.memory.modules.map((module, index) => (
                                <div className="demo-module-item" key={`${module.slot}-${index}`}>
                                    <h4>Module {index + 1} <span>· {module.slot}</span></h4>
                                    <dl className="demo-detail-grid">
                                        <div><dt>Capacity</dt><dd>{module.capacityGb} GB</dd></div>
                                        <div><dt>Type</dt><dd>{module.type}</dd></div>
                                        <div><dt>Speed</dt><dd>{formatOptional(module.speedMts, " MT/s")}</dd></div>
                                        <div><dt>Serial number</dt><dd>{formatOptional(module.serialNumber)}</dd></div>
                                    </dl>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="demo-hardware-card demo-hardware-card--third">
                        <div className="demo-card-title"><HardDrive size={17} aria-hidden="true" /><h3>Storage</h3></div>
                        <div className="demo-hardware-total"><span>Total installed storage</span><strong>{totalStorageGb} GB</strong></div>
                        <div className="demo-module-list">
                            {device.storage.drives.map((drive, index) => (
                                <div className="demo-module-item" key={`${drive.model}-${index}`}>
                                    <h4>Drive {index + 1}</h4>
                                    <dl className="demo-detail-grid">
                                        <div><dt>Model</dt><dd>{drive.model}</dd></div>
                                        <div><dt>Capacity</dt><dd>{drive.capacityGb} GB</dd></div>
                                        <div><dt>Type</dt><dd>{drive.type}</dd></div>
                                        <div><dt>Interface</dt><dd>{drive.interface}</dd></div>
                                        <div><dt>Serial number</dt><dd>{formatOptional(drive.serialNumber)}</dd></div>
                                    </dl>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="demo-hardware-card demo-hardware-card--half">
                        <div className="demo-card-title"><HardDrive size={17} aria-hidden="true" /><h3>BIOS / Firmware</h3></div>
                        <dl className="demo-detail-grid">
                            <div><dt>BIOS manufacturer</dt><dd>{device.bios.manufacturer}</dd></div>
                            <div><dt>BIOS version</dt><dd>{device.bios.version}</dd></div>
                            <div><dt>BIOS release date</dt><dd>{formatOptional(device.bios.releaseDate)}</dd></div>
                            <div><dt>System serial number</dt><dd>{formatOptional(device.systemSerialNumber)}</dd></div>
                        </dl>
                    </article>

                    <article className="demo-hardware-card demo-hardware-card--half">
                        <div className="demo-card-title"><Monitor size={17} aria-hidden="true" /><h3>Display</h3></div>
                        <dl className="demo-detail-grid">
                            <div><dt>Screen size</dt><dd>{formatOptional(device.display.screenSizeInches, " in")}</dd></div>
                            <div><dt>Current / native resolution</dt><dd>{formatOptional(device.display.resolution)}</dd></div>
                            <div><dt>Display manufacturer</dt><dd>{formatOptional(device.display.manufacturer)}</dd></div>
                            <div><dt>Graphics adapter</dt><dd>{device.display.graphicsAdapter}</dd></div>
                        </dl>
                    </article>
                </div>
            </section>

            <section aria-labelledby="sensor-monitoring-title">
                <div className="demo-section-heading">
                    <div className="demo-section-title">
                        <Thermometer size={19} aria-hidden="true" />
                        <h2 id="sensor-monitoring-title">Sensor Monitoring</h2>
                    </div>
                    <span className="demo-data-label">Sample readings · not live</span>
                </div>
                <div className="demo-sensor-grid">
                    {demoSensors.map((sensor) => {
                        const latest = sensor.readings?.[sensor.readings.length - 1];
                        return (
                            <article className="demo-sensor-card" key={sensor.id}>
                                <h3>{sensor.name}</h3>
                                <strong className="demo-sensor-reading">
                                    {latest === undefined ? "Not Available" : `${latest} ${sensor.unit}`}
                                </strong>
                                {sensor.readings && sensor.readings.length > 0 ? (
                                    <>
                                        <SensorChart name={sensor.name} unit={sensor.unit} readings={sensor.readings} />
                                        <span className="demo-sensor-caption">{sensor.readings.length} ordered sample readings</span>
                                    </>
                                ) : (
                                    <span className="demo-sensor-unavailable">Sensor data not available in this demo.</span>
                                )}
                            </article>
                        );
                    })}
                </div>
            </section>

            <section aria-labelledby="local-reports-title">
                <div className="demo-section-heading">
                    <div className="demo-section-title">
                        <FileText size={19} aria-hidden="true" />
                        <h2 id="local-reports-title">Local Reports</h2>
                    </div>
                    <span className="demo-data-label">Demo data</span>
                </div>
                <article className="demo-reports-summary">
                    <div>
                        <span className="demo-detail-label">Total Saved Reports</span>
                        <strong className="demo-reports-count">{reportCount}</strong>
                    </div>
                    <div>
                        <p>Reports stored on this device.</p>
                        <span className="demo-reports-disclaimer">Demo only — sample reports are not written to local storage.</span>
                    </div>
                </article>
            </section>

            <section className="demo-recent-panel" aria-labelledby="recent-reports-title">
                <div className="demo-section-heading">
                    <div className="demo-section-title">
                        <h2 id="recent-reports-title">Recent Inspection Reports</h2>
                    </div>
                    <button
                        className="button button-secondary demo-view-all"
                        type="button"
                        onClick={() => showDevelopmentNotice("The Reports page is under development.")}
                    >
                        VIEW ALL REPORTS
                    </button>
                </div>
                <div className="demo-report-table-wrap">
                    <table className="demo-report-table">
                        <thead>
                            <tr>
                                <th scope="col">Report ID</th>
                                <th scope="col">Device</th>
                                <th scope="col">Inspection Date</th>
                                <th scope="col">Result</th>
                                <th scope="col">Disposition</th>
                                <th scope="col"><span className="sr-only">Action</span></th>
                            </tr>
                        </thead>
                        <tbody>
                            {recentReports.map((report) => (
                                <tr key={report.reportId}>
                                    <td data-label="Report ID"><strong>{report.reportId}</strong></td>
                                    <td data-label="Device">{report.model}</td>
                                    <td data-label="Inspection Date">{formatInspectionDate(report.inspectionDate)}</td>
                                    <td data-label="Result">
                                        <span className={`demo-badge ${reportResultClass(report.result)}`}>
                                            {reportResultLabel(report.result)}
                                        </span>
                                    </td>
                                    <td data-label="Disposition">{report.disposition}</td>
                                    <td data-label="Action">
                                        <button
                                            className="demo-report-action"
                                            type="button"
                                            onClick={() => showDevelopmentNotice("The demo report viewer is under development.")}
                                            aria-label={`View demo report ${report.reportId}`}
                                        >
                                            View report
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>
        </main>
    );
}
