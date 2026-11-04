import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DeviceInformationCard({ title, values }: {
    title: string;
    values: Array<{ label: string; value: string | number | null | undefined }>;
}) {
    return (
        <Card>
            <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
            <CardContent>
                <dl className="device-specification-list">
                    {values.map(({ label, value }) => (
                        <div key={label}>
                            <dt>{label}</dt>
                            <dd>{value === null || value === undefined || value === "" ? "Not reported" : value}</dd>
                        </div>
                    ))}
                </dl>
            </CardContent>
        </Card>
    );
}
