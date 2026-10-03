import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getDevices } from "../api/devices";

interface Device {
    device_id: string;
    device_type: string;
    name: string;
    properties: Record<string, unknown>;
}

function formatValue(value: unknown): string {
    if (value === null || value === undefined) {
        return "-";
    }

    if (typeof value === "number") {
        return value.toLocaleString();
    }

    if (typeof value === "boolean") {
        return value ? "Yes" : "No";
    }

    return String(value);
}

function getPrimaryProperty(
    device: Device
): string {
    if (device.device_type === "cpu") {
        return `Cores: ${formatValue(
            device.properties.logical_cores
        )}`;
    }

    if (device.device_type === "memory") {
        return `Total: ${formatValue(
            device.properties.total_gb
        )} GB`;
    }

    if (device.device_type === "storage") {
        return `Total: ${formatValue(
            device.properties.total_gb
        )} GB`;
    }

    if (device.properties.manufacturer) {
        return `Manufacturer: ${formatValue(
            device.properties.manufacturer
        )}`;
    }

    return "Hardware device";
}

export default function DeviceDiscovery() {
    const navigate = useNavigate();

    const [devices, setDevices] =
        useState<Device[]>([]);

    const [loading, setLoading] =
        useState(false);

    const [error, setError] =
        useState<string | null>(null);

    async function loadDevices() {
        setLoading(true);
        setError(null);

        try {
            const data = await getDevices();
            setDevices(data);
        } catch {
            setError(
                "Failed to discover devices. Check that the UHDP backend is running."
            );
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadDevices();
    }, []);

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        Device Discovery
                    </h1>

                    <p className="page-description">
                        Hardware detected on the current machine.
                    </p>
                </div>

                <button
                    className="button button-primary"
                    onClick={loadDevices}
                    disabled={loading}
                >
                    {loading
                        ? "Discovering..."
                        : "Refresh Devices"}
                </button>
            </div>

            {error && (
                <div
                    className="error-box"
                    style={{ marginBottom: "20px" }}
                >
                    {error}
                </div>
            )}

            {!loading &&
                !error &&
                devices.length === 0 && (
                    <div className="card empty-state">
                        <div className="empty-state-title">
                            No devices discovered
                        </div>

                        <div>
                            Refresh the discovery process and try again.
                        </div>
                    </div>
                )}

            {devices.length > 0 && (
                <div className="device-grid">
                    {devices.map((device) => (
                        <div
                            className="device-card"
                            key={device.device_id}
                        >
                            <div className="device-card-header">
                                <div>
                                    <div className="device-type">
                                        {device.device_type}
                                    </div>

                                    <div className="device-name">
                                        {device.name}
                                    </div>
                                </div>
                            </div>

                            <div className="device-detail">
                                {getPrimaryProperty(device)}
                            </div>

                            <div className="device-id">
                                {device.device_id}
                            </div>

                            <div className="device-action">
                                <button
                                    className="button button-primary"
                                    onClick={() =>
                                        navigate(
                                            `/diagnostics?deviceId=${encodeURIComponent(
                                                device.device_id
                                            )}`
                                        )
                                    }
                                >
                                    Select Device
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}