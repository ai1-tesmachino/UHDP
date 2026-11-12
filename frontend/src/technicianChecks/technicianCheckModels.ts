import type { DiagnosticSession } from "../api/execution";

export type BackendOutcome = "passed" | "failed" | "warning" | "not_applicable" | "blocked" | "not_run";

export type PortType =
    | "USB-A"
    | "USB Type-C"
    | "HDMI"
    | "VGA"
    | "DisplayPort"
    | "SD card reader"
    | "Ethernet"
    | "Audio jack"
    | "Other";

export type PortOutcome = "Working" | "Not working" | "Intermittent" | "Physically damaged" | "Unable to verify";

export interface PortRecord {
    id: string;
    type: PortType;
    label: string;
    result: PortOutcome | null;
    notes: string;
    skipped: boolean;
    saved: boolean;
}

export interface KeyboardKey {
    code: string;
    label: string;
    width?: "wide" | "extra-wide" | "space";
}

export interface DeviceContext {
    deviceName: string;
    serial: string;
    displayResolution: string | null;
    refreshRateHz: number | null;
    displayName: string | null;
    connectors: Array<{ name: string; status: string }>;
    keyboardNames: string[];
    pointingDeviceNames: string[];
    hasTouchscreen: boolean;
    hasTouchpad: boolean;
    usbDevices: string[];
}

export const CHECK_IDS = {
    keyboard: "keyboard_input",
    touchscreen: "touchscreen",
    touchpad: "touchpad",
    touchpadGestures: "touchpad_gestures",
} as const;

export const PORT_CHECK_IDS: Record<PortType, string> = {
    "USB-A": "usb_port",
    "USB Type-C": "usb_c_port",
    HDMI: "hdmi_port",
    VGA: "vga_port",
    DisplayPort: "displayport",
    "SD card reader": "card_reader",
    Ethernet: "ethernet",
    "Audio jack": "headset_jack",
    Other: "ports_cosmetic",
};

export const portTypes: PortType[] = [
    "USB-A",
    "USB Type-C",
    "HDMI",
    "VGA",
    "DisplayPort",
    "SD card reader",
    "Ethernet",
    "Audio jack",
    "Other",
];

export const portOutcomes: PortOutcome[] = [
    "Working",
    "Not working",
    "Intermittent",
    "Physically damaged",
    "Unable to verify",
];

// The same 74-key US-QWERTY map used by the demo page. Kept local so the live
// page does not depend on demo-only modules.
function keyRow(codes: string[], labels = codes, widths: Array<KeyboardKey["width"]> = []): KeyboardKey[] {
    return codes.map((code, index) => ({
        code,
        label: labels[index],
        width: widths[index],
    }));
}

export const usQwertyKeyboardRows: KeyboardKey[][] = [
    keyRow(
        ["Escape", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
        ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
    ),
    keyRow(
        ["Backquote", "Digit1", "Digit2", "Digit3", "Digit4", "Digit5", "Digit6", "Digit7", "Digit8", "Digit9", "Digit0", "Minus", "Equal", "Backspace"],
        ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
        [undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, "wide"],
    ),
    keyRow(
        ["Tab", "KeyQ", "KeyW", "KeyE", "KeyR", "KeyT", "KeyY", "KeyU", "KeyI", "KeyO", "KeyP", "BracketLeft", "BracketRight", "Backslash"],
        ["Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"],
        ["wide"],
    ),
    keyRow(
        ["CapsLock", "KeyA", "KeyS", "KeyD", "KeyF", "KeyG", "KeyH", "KeyJ", "KeyK", "KeyL", "Semicolon", "Quote", "Enter"],
        ["Caps", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "Enter"],
        ["wide", undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, "wide"],
    ),
    keyRow(
        ["ShiftLeft", "KeyZ", "KeyX", "KeyC", "KeyV", "KeyB", "KeyN", "KeyM", "Comma", "Period", "Slash", "ShiftRight"],
        ["Shift", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Shift"],
        ["extra-wide", undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, "extra-wide"],
    ),
    keyRow(
        ["ControlLeft", "MetaLeft", "AltLeft", "Space", "AltRight", "MetaRight", "ContextMenu", "ControlRight"],
        ["Ctrl", "OS", "Alt", "Space", "Alt", "OS", "Menu", "Ctrl"],
        ["wide", undefined, undefined, "space", undefined, undefined, undefined, "wide"],
    ),
];

export const keyboardKeyCount = new Set(usQwertyKeyboardRows.flatMap((row) => row.map((key) => key.code))).size;

export function toBackendOutcome(value: string): BackendOutcome {
    switch (value.trim().toLowerCase()) {
        case "working correctly":
        case "working":
            return "passed";
        case "issues found":
        case "not working":
            return "failed";
        case "partially working":
        case "intermittent":
            return "warning";
        case "unable to verify":
            return "blocked";
        case "not applicable":
            return "not_applicable";
        default:
            return "not_run";
    }
}

export function decisionForOutcome(
    value: BackendOutcome,
): "working" | "not_working" | "unable_to_verify" | null {
    if (value === "passed") return "working";
    if (value === "failed") return "not_working";
    if (value === "blocked") return "unable_to_verify";
    return null;
}

export function aggregatePortOutcome(ports: PortRecord[]): BackendOutcome {
    const active = ports.filter((port) => !port.skipped);
    const withResults = active.filter((port) => port.result !== null);

    if (withResults.length === 0) return "not_run";
    if (withResults.some((port) => port.result === "Not working" || port.result === "Physically damaged")) {
        return "failed";
    }
    if (withResults.some((port) => port.result === "Intermittent")) return "warning";
    if (withResults.length < active.length) return "warning";
    if (withResults.every((port) => port.result === "Working")) return "passed";
    if (withResults.every((port) => port.result === "Unable to verify")) return "blocked";
    return "warning";
}

export function serializePortsEvidence(ports: PortRecord[]): Record<string, unknown> {
    return {
        source: "technician_checks",
        physical_ports: ports.map((port) => ({
            id: port.id,
            type: port.type,
            label: port.label,
            result: port.result,
            notes: port.notes.slice(0, 1000),
            skipped: port.skipped,
        })),
    };
}

function asRecord(value: unknown): Record<string, unknown> | null {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
    return value as Record<string, unknown>;
}

function asString(value: unknown): string {
    return typeof value === "string" ? value : "";
}

function asNumber(value: unknown): number | null {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asArray(value: unknown): unknown[] {
    return Array.isArray(value) ? value : [];
}

function isPortType(value: unknown): value is PortType {
    return typeof value === "string" && (portTypes as string[]).includes(value);
}

function isPortOutcome(value: unknown): value is PortOutcome {
    return typeof value === "string" && (portOutcomes as string[]).includes(value);
}

export function parsePortsEvidence(evidence: unknown, fallbackType: PortType): PortRecord[] {
    const record = asRecord(evidence);
    const rawPorts = Array.isArray(evidence) ? evidence : asArray(record?.physical_ports);
    const parsed: PortRecord[] = [];

    rawPorts.forEach((raw, index) => {
        const port = asRecord(raw);
        if (!port) return;
        const type = isPortType(port.type) ? port.type : fallbackType;
        const result = isPortOutcome(port.result) ? port.result : null;
        parsed.push({
            id: asString(port.id) || `${type.replace(/\s+/g, "-").toLowerCase()}-${index + 1}`,
            type,
            label: asString(port.label) || type,
            result,
            notes: asString(port.notes).slice(0, 1000),
            skipped: port.skipped === true,
            saved: true,
        });
    });

    return parsed;
}

export function serializeKeyboardEvidence(tested: string[], faulty: string[]): Record<string, unknown> {
    return {
        source: "technician_checks",
        keyboard: {
            tested_codes: [...new Set(tested)],
            faulty_codes: [...new Set(faulty)],
        },
    };
}

export function parseKeyboardEvidence(evidence: unknown): { tested: string[]; faulty: string[] } {
    const record = asRecord(evidence);
    const keyboard = asRecord(record?.keyboard) ?? record;
    const knownCodes = new Set(usQwertyKeyboardRows.flatMap((row) => row.map((key) => key.code)));
    const clean = (value: unknown) =>
        asArray(value).filter((code): code is string => typeof code === "string" && knownCodes.has(code));

    return {
        tested: [...new Set(clean(keyboard?.tested_codes))],
        faulty: [...new Set(clean(keyboard?.faulty_codes))],
    };
}

function inventoryDevice(session: DiagnosticSession, deviceType: string): Record<string, unknown> | null {
    const inventory = Array.isArray(session.device_inventory) ? session.device_inventory : [];
    for (const item of inventory) {
        const device = asRecord(item);
        if (device?.device_type === deviceType) return device;
    }
    return null;
}

function deviceProperties(device: Record<string, unknown> | null): Record<string, unknown> | null {
    return asRecord(device?.properties);
}

function inputDeviceNames(value: unknown): string[] {
    return asArray(value)
        .map((item) => asString(asRecord(item)?.name).trim())
        .filter(Boolean);
}

export function extractDeviceContext(session: DiagnosticSession): DeviceContext {
    const system = inventoryDevice(session, "system");
    const systemProperties = deviceProperties(system);
    const display = inventoryDevice(session, "display");
    const displayProperties = deviceProperties(display);
    const peripherals = inventoryDevice(session, "peripherals");
    const peripheralProperties = deviceProperties(peripherals);
    const inputDevices = asRecord(peripheralProperties?.input_devices);

    const keyboardNames = inputDeviceNames(inputDevices?.keyboards);
    const pointingDeviceNames = inputDeviceNames(
        Array.isArray(peripheralProperties?.pointing_devices)
            ? peripheralProperties?.pointing_devices
            : inputDevices?.pointing_devices,
    );
    const touchscreenNames = inputDeviceNames(inputDevices?.touchscreens);

    const connectors = asArray(displayProperties?.connectors)
        .map((item) => asRecord(item))
        .filter((item): item is Record<string, unknown> => item !== null)
        .map((item) => ({ name: asString(item.name), status: asString(item.status) }))
        .filter((item) => item.name);

    const usbDevices = asArray(peripheralProperties?.usb_devices)
        .map((item) => asRecord(item))
        .filter((item): item is Record<string, unknown> => item !== null)
        .map((item) => {
            const product = asString(item.product).trim();
            const manufacturer = asString(item.manufacturer).trim();
            if (product) return manufacturer && !product.includes(manufacturer) ? `${manufacturer} ${product}` : product;
            const ids = [asString(item.vendor_id), asString(item.product_id)].filter(Boolean).join(":");
            return ids || asString(item.sysfs_device);
        })
        .filter(Boolean);

    return {
        deviceName:
            asString(system?.name).trim() ||
            asString(systemProperties?.model).trim() ||
            session.device_id ||
            "Device not identified",
        serial: asString(systemProperties?.serial_number).trim() || "Not recorded",
        displayResolution: asString(displayProperties?.resolution).trim() || null,
        refreshRateHz: asNumber(displayProperties?.refresh_rate_hz),
        displayName: asString(displayProperties?.display_name).trim() || null,
        connectors,
        keyboardNames,
        pointingDeviceNames,
        hasTouchscreen: touchscreenNames.length > 0,
        hasTouchpad: pointingDeviceNames.some((name) => /touchpad|trackpad/i.test(name)),
        usbDevices,
    };
}

export function isTechnicianChecksComplete(input: {
    displayComplete: boolean;
    saved: Record<string, boolean>;
    ports: PortRecord[];
    portsFinalized: boolean;
}): boolean {
    const checksComplete = Object.values(CHECK_IDS).every((checkId) => input.saved[checkId] === true);
    const portsComplete = input.ports.length === 0
        ? true
        : input.portsFinalized && input.ports.every((port) => port.saved || port.skipped);
    return input.displayComplete && checksComplete && portsComplete;
}
