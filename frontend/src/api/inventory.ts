import api from "./client";
import { Device } from "../types/device";

export type InventoryValueSource = "detected" | "entered" | "corrected";

export interface InventoryField {
    value: unknown;
    source: InventoryValueSource;
    verified: boolean;
}

export interface StationInventory {
    fields: Record<string, InventoryField>;
    notes: Record<string, string>;
    custom_components: Array<{
        id: string;
        name: string;
        component_type: string;
        notes: string;
    }>;
    updated_at: string | null;
}

export interface MergedInventory {
    devices: Device[];
    inventory: StationInventory;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function flattenProperties(
    value: unknown,
    prefix: string,
    result: Record<string, unknown>,
) {
    if (Array.isArray(value)) {
        if (value.every((item) => !isRecord(item) && !Array.isArray(item))) {
            result[prefix] = value;
            return;
        }
        value.forEach((item, index) => flattenProperties(item, `${prefix}.${index}`, result));
        return;
    }
    if (isRecord(value)) {
        for (const [key, nested] of Object.entries(value)) {
            flattenProperties(nested, prefix ? `${prefix}.${key}` : key, result);
        }
        return;
    }
    if (prefix) result[prefix] = value;
}

function setNestedValue(target: Record<string, unknown>, path: string, value: unknown) {
    const parts = path.split(".");
    let current = target;
    for (const part of parts.slice(0, -1)) {
        const existing = current[part];
        if (!isRecord(existing) && !Array.isArray(existing)) current[part] = {};
        current = current[part] as Record<string, unknown>;
    }
    if (parts.length) current[parts[parts.length - 1]] = value;
}

export function inventoryFieldKey(deviceId: string, path: string) {
    return `${deviceId}.${path}`;
}

function shouldPreserveField(field?: InventoryField) {
    return Boolean(field && (field.verified || field.source === "entered" || field.source === "corrected"));
}

export function mergeDiscoveredInventory(
    devices: Device[],
    saved?: Partial<StationInventory>,
): MergedInventory {
    const fields: Record<string, InventoryField> = { ...(saved?.fields || {}) };
    const mergedDevices = devices.map((device) => {
        const discovered: Record<string, unknown> = {
            name: device.name,
            device_type: device.device_type,
        };
        flattenProperties(device.properties || {}, "properties", discovered);
        const effective: Record<string, unknown> = {};
        for (const [path, value] of Object.entries(discovered)) {
            const key = inventoryFieldKey(device.device_id, path);
            const existing = fields[key];
            if (shouldPreserveField(existing)) {
                effective[path] = existing.value;
            } else {
                fields[key] = { value, source: "detected", verified: false };
                effective[path] = value;
            }
        }
        for (const [key, field] of Object.entries(fields)) {
            const prefix = `${device.device_id}.`;
            if (key.startsWith(prefix) && shouldPreserveField(field)) {
                effective[key.slice(prefix.length)] = field.value;
            }
        }
        const properties = structuredClone(device.properties || {}) as Record<string, unknown>;
        for (const [path, value] of Object.entries(effective)) {
            if (path.startsWith("properties.")) {
                setNestedValue(properties, path.slice("properties.".length), value);
            }
        }
        return {
            ...device,
            name: String(effective.name ?? device.name),
            device_type: String(effective.device_type ?? device.device_type),
            properties,
        };
    });

    return {
        devices: mergedDevices,
        inventory: {
            fields,
            notes: { ...(saved?.notes || {}) },
            custom_components: [...(saved?.custom_components || [])],
            updated_at: saved?.updated_at || null,
        },
    };
}

export async function getStationInventory(): Promise<StationInventory> {
    const response = await api.get<StationInventory>("/devices/inventory");
    return response.data;
}

export async function saveStationInventory(
    inventory: Omit<StationInventory, "updated_at">,
): Promise<StationInventory> {
    const response = await api.put<StationInventory>("/devices/inventory", inventory);
    return response.data;
}
