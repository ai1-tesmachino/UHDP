import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getDevices } from "../api/devices";
import {
    InventoryField,
    inventoryFieldKey,
    mergeDiscoveredInventory,
    saveStationInventory,
    getStationInventory,
    StationInventory,
} from "../api/inventory";
import { Device } from "../types/device";

interface InventoryFieldDefinition {
    path: string;
    label: string;
}

const MEMORY_MODULE_FIELDS: Array<{ property: string; label: string; aliases: string[] }> = [
    { property: "bank", label: "Slot", aliases: ["bank", "BankLabel", "DeviceLocator"] },
    { property: "manufacturer", label: "Manufacturer", aliases: ["manufacturer", "Manufacturer"] },
    { property: "part_number", label: "Part number", aliases: ["part_number", "PartNumber", "model"] },
    { property: "serial_number", label: "Serial number", aliases: ["serial_number", "SerialNumber"] },
    { property: "capacity_gb", label: "Capacity (GB)", aliases: ["capacity_gb", "capacity_bytes", "Capacity"] },
    { property: "memory_type", label: "Type", aliases: ["memory_type", "MemoryType", "SMBIOSMemoryType"] },
    { property: "speed_mts", label: "Speed (MT/s)", aliases: ["speed_mts", "Speed", "ConfiguredClockSpeed"] },
];

const COMPONENT_FIELDS: Record<string, InventoryFieldDefinition[]> = {
    system: [
        { path: "properties.manufacturer", label: "Manufacturer" },
        { path: "properties.model", label: "Product name / model" },
        { path: "properties.serial_number", label: "Serial number" },
        { path: "properties.service_tag", label: "Product / service tag" },
        { path: "device_type", label: "Device type" },
        { path: "properties.uuid", label: "System UUID" },
        { path: "properties.bios_vendor", label: "BIOS manufacturer" },
        { path: "properties.bios_version", label: "BIOS version" },
        { path: "properties.bios_date", label: "BIOS date" },
        { path: "properties.bios_lock_status", label: "BIOS lock / password status" },
    ],
    cpu: [
        { path: "properties.vendor", label: "Processor manufacturer / vendor ID" },
        { path: "name", label: "Processor model" },
        { path: "properties.architecture", label: "Architecture" },
        { path: "properties.physical_cores", label: "Physical cores" },
        { path: "properties.logical_cores", label: "Logical cores" },
        { path: "properties.base_frequency_mhz", label: "Base frequency (MHz)" },
        { path: "properties.max_frequency_mhz", label: "Maximum frequency (MHz)" },
        { path: "properties.current_frequency_mhz", label: "Current frequency (MHz)" },
        { path: "properties.model_id", label: "CPU model identifier" },
    ],
    memory: [
        { path: "properties.total_gb", label: "Total RAM (GB)" },
        { path: "properties.used_bytes", label: "Used RAM (bytes)" },
        { path: "properties.available_bytes", label: "Available RAM (bytes)" },
        { path: "properties.physical_module_count", label: "Detected modules" },
        { path: "properties.reported_slot_count", label: "Reported memory slots" },
        { path: "properties.memory_configuration", label: "Memory configuration" },
    ],
    storage: [
        { path: "properties.manufacturer", label: "Manufacturer" },
        { path: "properties.model", label: "Model" },
        { path: "properties.serial_number", label: "Serial number" },
        { path: "properties.capacity_bytes", label: "Capacity (bytes)" },
        { path: "properties.interface", label: "Interface" },
        { path: "properties.protocol", label: "NVMe / SATA / other" },
        { path: "properties.firmware_version", label: "Firmware version" },
        { path: "properties.health", label: "Health information" },
        { path: "properties.smart_available", label: "SMART availability" },
        { path: "properties.partition_count", label: "Partition count" },
    ],
    gpu: [
        { path: "properties.manufacturer", label: "GPU manufacturer" },
        { path: "properties.name", label: "GPU model" },
        { path: "properties.adapter_type", label: "Integrated / discrete" },
        { path: "properties.vram_bytes", label: "VRAM (bytes)" },
        { path: "properties.driver_version", label: "Driver version" },
        { path: "properties.display_outputs", label: "Display outputs" },
    ],
    display: [
        { path: "properties.model", label: "Display model" },
        { path: "properties.resolution", label: "Resolution" },
        { path: "properties.refresh_rate_hz", label: "Refresh rate (Hz)" },
        { path: "properties.size_inches", label: "Display size (inches)" },
        { path: "properties.display_type", label: "Internal / external" },
        { path: "properties.connectors", label: "Connected display identifiers" },
    ],
    battery: [
        { path: "properties.manufacturer", label: "Manufacturer" },
        { path: "properties.model", label: "Model" },
        { path: "properties.serial_number", label: "Serial number" },
        { path: "properties.design_capacity_mwh", label: "Design capacity (mWh)" },
        { path: "properties.full_charge_capacity_mwh", label: "Full charge capacity (mWh)" },
        { path: "properties.current_charge_mwh", label: "Current charge (mWh)" },
        { path: "properties.cycle_count", label: "Cycle count" },
        { path: "properties.health_percent", label: "Health (%)" },
        { path: "properties.charging_status", label: "Charging status" },
        { path: "properties.ac_adapter_status", label: "AC adapter status" },
    ],
    network: [
        { path: "name", label: "Adapter" },
        { path: "properties.manufacturer", label: "Manufacturer" },
        { path: "properties.connection_type", label: "Connection type" },
        { path: "properties.mac_address", label: "MAC address" },
    ],
};

const TYPE_LABELS: Record<string, string> = {
    system: "System identification",
    cpu: "Processor",
    memory: "RAM",
    storage: "Storage",
    storage_inventory: "Storage",
    gpu: "Graphics",
    display: "Display",
    battery: "Battery",
    network: "Connectivity and peripherals",
    peripherals: "Connectivity and peripherals",
    motherboard: "System board",
    audio: "Audio devices",
};

function displayLabel(path: string) {
    const name = path.split(".").at(-1) || path;
    return name.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function displayValue(value: unknown): string {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    return JSON.stringify(value);
}

function shouldHideSensitiveField(path: string) {
    return /(^|\.)(mountpoint|mounted_filesystems|mounts|user_files|home_directory|file_list|partition_details)(\.|$)/i.test(path);
}

function fieldValue(fields: Record<string, InventoryField>, deviceId: string, path: string) {
    return fields[inventoryFieldKey(deviceId, path)];
}

function getDeviceFields(device: Device, fields: Record<string, InventoryField>) {
    const prefix = `${device.device_id}.`;
    const availablePaths = Object.keys(fields)
        .filter((key) => key.startsWith(prefix))
        .map((key) => key.slice(prefix.length))
        .filter((path) => !shouldHideSensitiveField(path));
    const expected = COMPONENT_FIELDS[device.device_type.toLowerCase()] || [];
    const paths = [...expected.map((field) => field.path), ...availablePaths];
    return [...new Set(paths)].map((path) => ({
        path,
        label: expected.find((field) => field.path === path)?.label || displayLabel(path),
        record: fieldValue(fields, device.device_id, path),
    }));
}

function sourceLabel(source: InventoryField["source"]) {
    if (source === "entered") return "Technician entered";
    if (source === "corrected") return "Technician corrected";
    return "Automatically detected";
}

function groupLabel(type: string) {
    return TYPE_LABELS[type.toLowerCase()] || type.replaceAll("_", " ");
}

export default function Dashboard() {
    const navigate = useNavigate();
    const [devices, setDevices] = useState<Device[]>([]);
    const [inventory, setInventory] = useState<StationInventory>({
        fields: {},
        notes: {},
        custom_components: [],
        updated_at: null,
    });
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [savedAt, setSavedAt] = useState<string | null>(null);
    const [customName, setCustomName] = useState("");
    const [customType, setCustomType] = useState("");
    const [customNotes, setCustomNotes] = useState("");

    const loadInventory = useCallback(async (refreshingNow = false) => {
        setRefreshing(refreshingNow);
        if (!refreshingNow) setLoading(true);
        setError("");
        try {
            const [discovered, stored] = await Promise.all([getDevices(), getStationInventory()]);
            const merged = mergeDiscoveredInventory(discovered, stored);
            setDevices(merged.devices);
            setInventory(merged.inventory);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Hardware inventory could not be loaded.");
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        void loadInventory();
    }, [loadInventory]);

    const groups = useMemo(() => {
        const order = ["system", "cpu", "memory", "storage", "gpu", "display", "battery", "network", "peripherals"];
        return [...devices].sort((a, b) => {
            const ai = order.indexOf(a.device_type.toLowerCase());
            const bi = order.indexOf(b.device_type.toLowerCase());
            return (ai < 0 ? order.length : ai) - (bi < 0 ? order.length : bi);
        });
    }, [devices]);

    function updateField(device: Device, path: string, rawValue: string) {
        const key = inventoryFieldKey(device.device_id, path);
        const existing = inventory.fields[key];
        setInventory((current) => ({
            ...current,
            fields: {
                ...current.fields,
                [key]: {
                    value: rawValue,
                    source: existing?.source === "detected" && existing.value !== null && existing.value !== undefined
                        ? "corrected"
                        : existing?.source || "entered",
                    verified: false,
                },
            },
        }));
    }

    function addMissingField(device: Device) {
        const fieldName = window.prompt("Enter the name of the missing specification:");
        if (!fieldName?.trim()) return;
        const path = `technician.${fieldName.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
        const key = inventoryFieldKey(device.device_id, path);
        setInventory((current) => ({
            ...current,
            fields: {
                ...current.fields,
                [key]: { value: "", source: "entered", verified: false },
            },
        }));
    }

    function addCustomComponent(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const name = customName.trim();
        if (!name) return;
        setInventory((current) => ({
            ...current,
            custom_components: [
                ...current.custom_components,
                {
                    id: typeof crypto !== "undefined" && crypto.randomUUID
                        ? crypto.randomUUID()
                        : `${Date.now()}_${Math.random().toString(16).slice(2)}`,
                    name,
                    component_type: customType.trim() || "Other component",
                    notes: customNotes.trim(),
                },
            ],
        }));
        setCustomName("");
        setCustomType("");
        setCustomNotes("");
    }

    async function saveInventory() {
        setSaving(true);
        setError("");
        try {
            const record = await saveStationInventory({
                fields: inventory.fields,
                notes: inventory.notes,
                custom_components: inventory.custom_components,
            });
            setInventory(record);
            setSavedAt(record.updated_at);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Hardware inventory could not be saved.");
        } finally {
            setSaving(false);
        }
    }

    function verifyField(device: Device, path: string, verified: boolean) {
        const key = inventoryFieldKey(device.device_id, path);
        const existing = inventory.fields[key];
        setInventory((current) => ({
            ...current,
            fields: {
                ...current.fields,
                [key]: {
                    value: existing?.value ?? "",
                    source: existing?.source || "entered",
                    verified,
                },
            },
        }));
    }

    return (
        <div className="page-flow inventory-dashboard">
            <header className="page-header inventory-page-header">
                <div>
                    <span className="eyebrow">WORKSPACE / HARDWARE INVENTORY</span>
                    <h1 className="page-title">Hardware Inventory</h1>
                    <p className="page-description">
                        Compare detected specifications with the physical device, correct values, and save a verified station inventory.
                    </p>
                </div>
                <div className="action-row">
                    <button className="button button-secondary" type="button" onClick={() => void loadInventory(true)} disabled={loading || refreshing}>
                        {refreshing ? "Refreshing…" : "Refresh hardware"}
                    </button>
                    <button className="button button-primary" type="button" onClick={() => void saveInventory()} disabled={loading || saving}>
                        {saving ? "Saving inventory…" : "Save inventory"}
                    </button>
                    <button className="button button-secondary" type="button" onClick={() => navigate("/devices?new=1")}>
                        Continue to QC intake →
                    </button>
                </div>
            </header>

            <div className="inventory-save-banner">
                <span>Field source is shown for every value. Verified or technician-edited values are preserved on refresh.</span>
                <span>{savedAt || inventory.updated_at ? `Last saved ${new Date(savedAt || inventory.updated_at || "").toLocaleString()}` : "Not saved yet"}</span>
            </div>
            {error && <div className="error-box" role="alert">{error}</div>}

            {loading ? (
                <div className="loading-panel">Discovering hardware inventory…</div>
            ) : devices.length === 0 ? (
                <section className="empty-panel">
                    <h2>No hardware inventory reported</h2>
                    <p>Check that the local UHDP service is available, then refresh discovery.</p>
                    <button className="button button-primary" type="button" onClick={() => void loadInventory(true)}>Refresh hardware</button>
                </section>
            ) : (
                <div className="inventory-component-list">
                    {groups.map((device, index) => {
                        const componentType = device.device_type.toLowerCase();
                        const isMemory = componentType === "memory";
                        const modules = Array.isArray(device.properties.memory_modules)
                            ? device.properties.memory_modules.filter((item): item is Record<string, unknown> =>
                                typeof item === "object" && item !== null && !Array.isArray(item),
                            )
                            : [];
                        const disks = Array.isArray(device.properties.physical_disks)
                            ? device.properties.physical_disks.filter((item): item is Record<string, unknown> =>
                                typeof item === "object" && item !== null && !Array.isArray(item),
                            )
                            : [];
                        const fields = getDeviceFields(device, inventory.fields);
                        return (
                            <details className="inventory-component-card" key={`${device.device_id}-${index}`} open={index === 0}>
                                <summary>
                                    <span className="inventory-component-title">
                                        <span className="device-type-pill">{groupLabel(device.device_type)}</span>
                                        <strong>{device.name || groupLabel(device.device_type)}</strong>
                                    </span>
                                    <span className="inventory-component-count">{fields.length} specifications · Expand</span>
                                </summary>
                                <div className="inventory-card-body">
                                    {isMemory && (
                                        <div className="inventory-ram-summary">
                                            <strong>{String(device.properties.total_gb ?? "Not reported")} GB total RAM</strong>
                                            <span>{modules.length} module records · {String(device.properties.installed_slots ?? "Slots not reported")} slots reported</span>
                                            {device.properties.module_inventory_warning != null && <small>{String(device.properties.module_inventory_warning)}</small>}
                                        </div>
                                    )}
                                    {isMemory && modules.length > 0 && (
                                        <section className="inventory-memory-modules">
                                            <h3>Physical memory modules</h3>
                                            <div className="inventory-module-grid">
                                                {modules.map((module, moduleIndex) => (
                                                    <article className="inventory-module-card" key={`${device.device_id}-module-${moduleIndex}`}>
                                                        <h4>Module {moduleIndex + 1} · {String(module.bank || module.BankLabel || module.DeviceLocator || `Slot ${moduleIndex + 1}`)}</h4>
                                                        {MEMORY_MODULE_FIELDS.map(({ property, label, aliases }) => {
                                                            const key = aliases.find((alias) =>
                                                                Object.prototype.hasOwnProperty.call(module, alias),
                                                            ) || String(property);
                                                            const path = `properties.memory_modules.${moduleIndex}.${key}`;
                                                            const record = fieldValue(inventory.fields, device.device_id, path);
                                                            const rawValue = record?.value ?? module[key];
                                                            const value = property === "capacity_gb" && key !== "capacity_gb" && rawValue !== undefined
                                                                ? Number(rawValue) / (1024 ** 3)
                                                                : rawValue;
                                                            const source = record?.source || "detected";
                                                            return (
                                                                <label className="inventory-field" key={property}>
                                                                    <span>{label}</span>
                                                                    <input
                                                                        value={displayValue(value)}
                                                                        placeholder="Not reported"
                                                                        onChange={(event) => updateField(
                                                                            device,
                                                                            path,
                                                                            property === "capacity_gb" && key !== "capacity_gb" && event.target.value
                                                                                ? String(Number(event.target.value) * (1024 ** 3))
                                                                                : event.target.value,
                                                                        )}
                                                                    />
                                                                    <small>{sourceLabel(source)}{record?.verified ? " · Verified" : ""}</small>
                                                                    <label className="inventory-verify">
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={Boolean(record?.verified)}
                                                                            onChange={(event) => verifyField(device, path, event.target.checked)}
                                                                        />
                                                                        Manually verified
                                                                    </label>
                                                                </label>
                                                            );
                                                        })}
                                                    </article>
                                                ))}
                                            </div>
                                        </section>
                                    )}
                                    {componentType === "storage" && disks.length > 0 && (
                                        <section className="inventory-memory-modules">
                                            <h3>Physical storage devices</h3>
                                            <div className="inventory-module-grid">
                                                {disks.map((disk, diskIndex) => (
                                                    <article className="inventory-module-card" key={`${device.device_id}-disk-${diskIndex}`}>
                                                        <h4>Drive {diskIndex + 1} · {String(disk.model || disk.name || "Model not reported")}</h4>
                                                        {[
                                                            ["manufacturer", "Manufacturer"],
                                                            ["model", "Model"],
                                                            ["serial_number", "Serial number"],
                                                            ["capacity_bytes", "Capacity (bytes)"],
                                                            ["interface", "Interface"],
                                                            ["protocol", "NVMe / SATA / other"],
                                                            ["firmware_version", "Firmware"],
                                                            ["health", "Health"],
                                                            ["smart_available", "SMART availability"],
                                                        ].map(([property, label]) => {
                                                            const path = `properties.physical_disks.${diskIndex}.${property}`;
                                                            const record = fieldValue(inventory.fields, device.device_id, path);
                                                            return (
                                                                <label className="inventory-field" key={property}>
                                                                    <span>{label}</span>
                                                                    <input
                                                                        value={displayValue(record?.value ?? disk[property])}
                                                                        placeholder="Not reported"
                                                                        onChange={(event) => updateField(device, path, event.target.value)}
                                                                    />
                                                                    <small>{sourceLabel(record?.source || "detected")}{record?.verified ? " · Verified" : ""}</small>
                                                                    <label className="inventory-verify">
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={Boolean(record?.verified)}
                                                                            onChange={(event) => verifyField(device, path, event.target.checked)}
                                                                        />
                                                                        Manually verified
                                                                    </label>
                                                                </label>
                                                            );
                                                        })}
                                                        {Array.isArray(disk.partitions) && disk.partitions.length > 0 && (
                                                            <div className="inventory-partitions">
                                                                <strong>{disk.partitions.length} partition records</strong>
                                                                {disk.partitions.map((partition, partitionIndex) => {
                                                                    if (typeof partition !== "object" || partition === null || Array.isArray(partition)) return null;
                                                                    const safePartition = partition as Record<string, unknown>;
                                                                    return (
                                                                        <span key={partitionIndex}>
                                                                            {[safePartition.name, safePartition.filesystem, safePartition.size_bytes ?? safePartition.capacity_bytes]
                                                                                .filter((value) => value !== null && value !== undefined && value !== "")
                                                                                .map(String)
                                                                                .join(" · ") || `Partition ${partitionIndex + 1}`}
                                                                        </span>
                                                                    );
                                                                })}
                                                                <small>Mount paths and user files are not displayed.</small>
                                                            </div>
                                                        )}
                                                    </article>
                                                ))}
                                            </div>
                                        </section>
                                    )}
                                    <div className="inventory-fields-grid">
                                        {fields
                                            .filter((field) => !(isMemory && field.path.startsWith("properties.memory_modules.")))
                                            .filter((field) => !(componentType === "storage" && field.path.startsWith("properties.physical_disks.")))
                                            .map(({ path, label, record }) => {
                                                const metadata = record || {
                                                    value: null,
                                                    source: "detected" as const,
                                                    verified: false,
                                                };
                                                const batteries = Array.isArray(device.properties.batteries)
                                                    ? device.properties.batteries.filter((item): item is Record<string, unknown> =>
                                                        typeof item === "object" && item !== null && !Array.isArray(item),
                                                    )
                                                    : [];
                                                const battery = batteries[0] || device.properties;
                                                const designCapacity = Number(
                                                    battery.energy_full_design_uwh ?? battery.charge_full_design_uah ??
                                                    battery.design_capacity_mwh,
                                                );
                                                const fullCapacity = Number(
                                                    battery.energy_full_uwh ?? battery.charge_full_uah ??
                                                    battery.full_charge_capacity_mwh,
                                                );
                                                const batteryHealth = componentType === "battery" &&
                                                    path === "properties.health_percent" &&
                                                    (metadata.value === null || metadata.value === undefined || metadata.value === "") &&
                                                    Number.isFinite(designCapacity) && designCapacity > 0 &&
                                                    Number.isFinite(fullCapacity)
                                                    ? fullCapacity / designCapacity * 100
                                                    : null;
                                                return (
                                                    <label className="inventory-field" key={path}>
                                                        <span>{label}</span>
                                                        <input
                                                            value={displayValue(batteryHealth ?? metadata.value)}
                                                            placeholder={batteryHealth === null ? "Not reported — enter if verified" : ""}
                                                            onChange={(event) => updateField(device, path, event.target.value)}
                                                        />
                                                        <small>{sourceLabel(metadata.source)}{metadata.verified ? " · Verified" : ""}</small>
                                                        {batteryHealth !== null && <small>Calculated: full charge capacity ÷ design capacity × 100</small>}
                                                        <label className="inventory-verify">
                                                            <input
                                                                type="checkbox"
                                                                checked={metadata.verified}
                                                                onChange={(event) => verifyField(device, path, event.target.checked)}
                                                            />
                                                            Manually verified
                                                        </label>
                                                    </label>
                                                );
                                            })}
                                    </div>
                                    {fields.some((field) => field.path.startsWith("properties.inventory_warnings")) && (
                                        <p className="inventory-unavailable-note">Some specifications were unavailable from firmware or this station. Unavailable values are left blank rather than inferred.</p>
                                    )}
                                    <label className="inventory-notes-field">
                                        Technician notes
                                        <textarea
                                            rows={2}
                                            maxLength={4000}
                                            value={inventory.notes[device.device_id] || ""}
                                            onChange={(event) => setInventory((current) => ({
                                                ...current,
                                                notes: { ...current.notes, [device.device_id]: event.target.value },
                                            }))}
                                            placeholder="Add inventory notes"
                                        />
                                    </label>
                                    <button className="button button-quiet" type="button" onClick={() => addMissingField(device)}>
                                        + Add missing specification
                                    </button>
                                </div>
                            </details>
                        );
                    })}
                    {inventory.custom_components.map((component) => (
                        <details className="inventory-component-card" key={component.id}>
                            <summary>
                                <span className="inventory-component-title">
                                    <span className="device-type-pill">Technician entered</span>
                                    <strong>{component.name}</strong>
                                </span>
                                <span className="inventory-component-count">{component.component_type}</span>
                            </summary>
                            <div className="inventory-card-body">
                                <p>{component.notes || "No notes recorded."}</p>
                                <span className="inventory-field-source">Technician entered · Manually verified by entry</span>
                            </div>
                        </details>
                    ))}
                </div>
            )}

            <form className="inventory-add-component" onSubmit={addCustomComponent}>
                <h2>Add missing component</h2>
                <label>
                    Component name
                    <input value={customName} maxLength={150} onChange={(event) => setCustomName(event.target.value)} required />
                </label>
                <label>
                    Component type
                    <input value={customType} maxLength={100} onChange={(event) => setCustomType(event.target.value)} placeholder="For example, card reader" />
                </label>
                <label>
                    Notes
                    <input value={customNotes} maxLength={1000} onChange={(event) => setCustomNotes(event.target.value)} />
                </label>
                <button className="button button-secondary" type="submit">Add component</button>
            </form>

            <footer className="inventory-footer">
                <span>Save inventory before starting intake to keep all technician-entered values.</span>
                <button className="button button-primary" type="button" onClick={() => void saveInventory()} disabled={saving}>
                    {saving ? "Saving…" : "Save inventory"}
                </button>
            </footer>
        </div>
    );
}
