import { demoDevice } from "./demoDevice";

export type ManualCheckCategoryId = "display" | "keyboard" | "touchscreen" | "touchpad";
export type ManualCheckOutcome =
    | "Working correctly"
    | "Issues found"
    | "Partially working"
    | "Not working"
    | "Unable to verify"
    | "Not Applicable";
export type PortCheckOutcome =
    | "Working"
    | "Not Working"
    | "Intermittent"
    | "Physically Damaged"
    | "Unable to Verify";

export interface ManualCheckRecord {
    hardwareIdentifier: string;
    result: ManualCheckOutcome | null;
    notes: string;
    completed: boolean;
}

export interface PortCheckRecord {
    id: string;
    type: string;
    label: string;
    result: PortCheckOutcome | null;
    notes: string;
    completed: boolean;
    skipped: boolean;
}

export interface ManualFunctionalChecksState {
    checks: Record<ManualCheckCategoryId, ManualCheckRecord>;
    testedKeyCodes: string[];
    faultyKeyCodes: string[];
    ports: PortCheckRecord[];
    portsFinalized: boolean;
}

export interface ManualCheckSummary {
    totalSelected: number;
    completed: number;
    passed: number;
    failed: number;
    unableToVerify: number;
    notApplicable: number;
    notTested: number;
}

export interface KeyboardKey {
    code: string;
    label: string;
    width?: "wide" | "extra-wide" | "space";
}

export const portTypes = [
    "USB-A",
    "USB Type-C",
    "HDMI",
    "VGA",
    "DisplayPort",
    "SD card reader",
    "Ethernet",
    "Audio jack",
    "Other",
] as const;

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

function createCheck(hardwareIdentifier: string, result: ManualCheckOutcome | null = null, completed = false): ManualCheckRecord {
    return { hardwareIdentifier, result, notes: "", completed };
}

export function createInitialManualFunctionalChecks(): ManualFunctionalChecksState {
    const touchscreenPresent = demoDevice.display.touchscreenPresent;
    return {
        checks: {
            display: createCheck(`${demoDevice.display.manufacturer ?? "Display"} · ${demoDevice.display.resolution ?? "resolution unavailable"}`),
            keyboard: createCheck(`${demoDevice.keyboard.layout} · ${demoDevice.keyboard.type}`),
            touchscreen: createCheck(
                touchscreenPresent ? "Integrated touchscreen" : "Touchscreen not detected",
                touchscreenPresent ? null : "Not Applicable",
                !touchscreenPresent,
            ),
            touchpad: createCheck(demoDevice.touchpad.present ? demoDevice.touchpad.type : "Touchpad not detected"),
        },
        testedKeyCodes: [],
        faultyKeyCodes: [],
        ports: [],
        portsFinalized: false,
    };
}

export function summarizeManualFunctionalChecks(state: ManualFunctionalChecksState): ManualCheckSummary {
    const records = [...Object.values(state.checks), ...state.ports];
    const totalSelected = records.length;
    const notApplicable = records.filter((record) => record.result === "Not Applicable").length;
    const completedRecords = records.filter((record) => record.completed && record.result !== null && record.result !== "Not Applicable");
    const isPassed = (result: string | null) => result === "Working correctly" || result === "Working";
    const isFailed = (result: string | null) =>
        result === "Issues found"
        || result === "Partially working"
        || result === "Not working"
        || result === "Not Working"
        || result === "Intermittent"
        || result === "Physically Damaged";
    const unableToVerify = completedRecords.filter((record) => record.result === "Unable to verify" || record.result === "Unable to Verify").length;
    const passed = completedRecords.filter((record) => isPassed(record.result)).length;
    const failed = completedRecords.filter((record) => isFailed(record.result)).length;
    const completed = completedRecords.length;

    return {
        totalSelected,
        completed,
        passed,
        failed,
        unableToVerify,
        notApplicable,
        notTested: totalSelected - completed - notApplicable,
    };
}

export function isManualFunctionalChecksComplete(state: ManualFunctionalChecksState): boolean {
    const categoriesComplete = Object.entries(state.checks)
        .every(([category, record]) => category === "touchscreen" && !demoDevice.display.touchscreenPresent
            ? record.result === "Not Applicable"
            : record.completed && record.result !== null);
    const selectedPortsReviewed = state.ports.every((port) => port.completed || port.skipped);
    return categoriesComplete && state.portsFinalized && selectedPortsReviewed;
}
