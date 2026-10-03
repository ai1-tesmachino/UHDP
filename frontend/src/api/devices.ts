import { Device } from "../types/device";
import api from "./client";

export async function getDevices(): Promise<Device[]> {
    const response = await api.get<Device[]>("/devices/");

    return response.data;
}

export async function getDevice(deviceId: string): Promise<Device> {
    const response = await api.get<Device>(
        `/devices/${encodeURIComponent(deviceId)}`
    );

    return response.data;
}