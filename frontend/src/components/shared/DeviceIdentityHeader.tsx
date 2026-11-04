import { Badge } from "@/components/ui/badge";

export function DeviceIdentityHeader({ name, serialNumber, qcId, status }: {
    name: string;
    serialNumber?: string | null;
    qcId?: string | null;
    status?: string;
}) {
    return (
        <header className="device-identity-header">
            <div>
                <h2>{name || "Device not identified"}</h2>
                <p>Serial number: {serialNumber || "Not recorded"}</p>
            </div>
            <div className="device-identity-badges">
                {qcId && <Badge variant="outline">{qcId}</Badge>}
                {status && <Badge variant="secondary">{status.replaceAll("_", " ")}</Badge>}
            </div>
        </header>
    );
}
