export interface Device {
    device_id: string;
    device_type: string;
    name: string;
    properties: Record<string, unknown>;
}