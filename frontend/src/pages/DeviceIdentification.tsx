import { useNavigate, Link } from "react-router-dom";
import type { ReactNode } from "react";
import { ClipboardList, Cpu, HardDrive, MemoryStick, Monitor } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { demoDevice, getTotalInstalledRamGb, getTotalInstalledStorageGb } from "../demo/demoDevice";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import { PageHeader } from "../components/shared/PageHeader";
import InspectionProgress from "../components/shared/InspectionProgress";
import { isPhysicalAssessmentComplete } from "../demo/physicalAssessment";
import { isHardwareDiagnosticsComplete } from "../demo/hardwareDiagnostics";
import "./device-identification.css";

function formatValue(value: string | number | null | undefined, suffix = "") {
    return value === null || value === undefined || value === ""
        ? "Not Available"
        : `${value}${suffix}`;
}

function formatFrequency(value: number | null) {
    return value === null ? "Not Available" : `${value.toFixed(2)} GHz`;
}

function DetailGrid({ fields }: { fields: Array<{ label: string; value: string; emphasized?: boolean }> }) {
    return (
        <dl className="device-id-detail-grid">
            {fields.map((field) => (
                <div className={field.emphasized ? "is-emphasized" : undefined} key={field.label}>
                    <dt>{field.label}</dt>
                    <dd>{field.value}</dd>
                </div>
            ))}
        </dl>
    );
}

function InformationCard({
    title,
    icon: Icon,
    children,
    className = "",
}: {
    title: string;
    icon: LucideIcon;
    children: ReactNode;
    className?: string;
}) {
    return (
        <section className={`device-id-card ${className}`.trim()}>
            <div className="device-id-card-heading">
                <Icon size={18} aria-hidden="true" />
                <h2>{title}</h2>
            </div>
            {children}
        </section>
    );
}

export default function DeviceIdentification() {
    const navigate = useNavigate();
    const {
        assetTag,
        setAssetTag,
        technicianName,
        setTechnicianName,
        deviceConfirmed,
        confirmDevice,
        physicalAssessments,
        diagnosticResults,
    } = useDemoInspection();
    const totalRamGb = getTotalInstalledRamGb(demoDevice);
    const totalStorageGb = getTotalInstalledStorageGb(demoDevice);

    function confirmAndContinue() {
        confirmDevice();
        navigate("/physical-assessment");
    }

    return (
        <main className="device-identification page-flow" aria-labelledby="device-identification-title">
            <PageHeader
                title="Device Identification"
                titleId="device-identification-title"
                description="Verify the detected hardware information before starting the inspection."
                eyebrow="DEVICE INSPECTION"
                actions={<span className="device-id-demo-label">DEMO DATA</span>}
            />

            <InspectionProgress
                activeStage={0}
                deviceConfirmed={deviceConfirmed}
                physicalAssessmentComplete={isPhysicalAssessmentComplete(physicalAssessments)}
                diagnosticsComplete={isHardwareDiagnosticsComplete(diagnosticResults)}
            />

            <div className="device-id-card-grid">
                <InformationCard title="Device Information" icon={HardDrive}>
                    <DetailGrid fields={[
                        { label: "Manufacturer", value: demoDevice.manufacturer },
                        { label: "Model", value: demoDevice.model },
                        { label: "System serial number", value: formatValue(demoDevice.systemSerialNumber), emphasized: true },
                        { label: "BIOS manufacturer", value: demoDevice.bios.manufacturer },
                        { label: "BIOS version", value: demoDevice.bios.version },
                        { label: "BIOS release date", value: formatValue(demoDevice.bios.releaseDate) },
                        { label: "BIOS serial number", value: formatValue(demoDevice.bios.serialNumber) },
                    ]} />
                </InformationCard>

                <InformationCard title="Processor" icon={Cpu}>
                    <DetailGrid fields={[
                        { label: "CPU manufacturer", value: demoDevice.processor.manufacturer },
                        { label: "CPU model", value: demoDevice.processor.model },
                        { label: "Physical cores", value: formatValue(demoDevice.processor.physicalCores) },
                        { label: "Logical threads", value: formatValue(demoDevice.processor.logicalThreads) },
                        { label: "Base frequency", value: formatFrequency(demoDevice.processor.baseFrequencyGhz) },
                        { label: "Maximum frequency", value: formatFrequency(demoDevice.processor.maxFrequencyGhz) },
                    ]} />
                </InformationCard>

                <InformationCard title="Memory" icon={MemoryStick}>
                    <div className="device-id-total">
                        <span>Total installed RAM</span>
                        <strong>
                            {totalRamGb} GB <span>| {demoDevice.memory.modules.length} Modules</span>
                        </strong>
                    </div>
                    <div className="device-id-module-list">
                        {demoDevice.memory.modules.map((module, index) => (
                            <div className="device-id-module" key={`${module.slot}-${index}`}>
                                <h3>Module {index + 1} <span>· {module.slot}</span></h3>
                                <DetailGrid fields={[
                                    { label: "Capacity", value: formatValue(module.capacityGb, " GB") },
                                    { label: "Memory type", value: formatValue(module.type) },
                                    { label: "Speed", value: formatValue(module.speedMts, " MT/s") },
                                    { label: "Serial number", value: formatValue(module.serialNumber) },
                                ]} />
                            </div>
                        ))}
                    </div>
                </InformationCard>

                <InformationCard title="Storage" icon={HardDrive}>
                    <div className="device-id-total">
                        <span>Total installed physical storage</span>
                        <strong>
                            {totalStorageGb} GB <span>| {demoDevice.storage.drives.length} {demoDevice.storage.drives.length === 1 ? "Drive" : "Drives"}</span>
                        </strong>
                    </div>
                    <div className="device-id-module-list">
                        {demoDevice.storage.drives.map((drive, index) => (
                            <div className="device-id-module" key={`${drive.model}-${index}`}>
                                <h3>Drive {index + 1}</h3>
                                <DetailGrid fields={[
                                    { label: "Model", value: drive.model },
                                    { label: "Capacity", value: formatValue(drive.capacityGb, " GB") },
                                    { label: "Drive type", value: formatValue(drive.type) },
                                    { label: "Interface", value: formatValue(drive.interface) },
                                    { label: "Serial number", value: formatValue(drive.serialNumber) },
                                ]} />
                            </div>
                        ))}
                    </div>
                </InformationCard>

                <InformationCard title="Display" icon={Monitor}>
                    <DetailGrid fields={[
                        { label: "Physical screen size", value: formatValue(demoDevice.display.screenSizeInches, " inches") },
                        { label: "Resolution", value: formatValue(demoDevice.display.resolution) },
                        { label: "Display manufacturer", value: formatValue(demoDevice.display.manufacturer) },
                        { label: "Graphics adapter", value: demoDevice.display.graphicsAdapter },
                    ]} />
                </InformationCard>

                <InformationCard title="Asset Information" icon={ClipboardList} className="device-id-asset-card">
                    <div className="device-id-asset-fields">
                        <label>
                            <span>Asset Tag</span>
                            <input
                                className="device-id-input"
                                type="text"
                                name="assetTag"
                                autoComplete="off"
                                value={assetTag}
                                onChange={(event) => setAssetTag(event.target.value)}
                            />
                        </label>
                        <label>
                            <span>Technician Name</span>
                            <input
                                className="device-id-input"
                                type="text"
                                name="technicianName"
                                autoComplete="off"
                                value={technicianName}
                                onChange={(event) => setTechnicianName(event.target.value)}
                            />
                        </label>
                    </div>
                </InformationCard>
            </div>

            <footer className="device-id-actions">
                <Link className="button button-secondary" to="/">Back to Dashboard</Link>
                <button className="button button-primary" type="button" onClick={confirmAndContinue}>
                    CONFIRM DEVICE &amp; CONTINUE
                </button>
            </footer>
        </main>
    );
}
