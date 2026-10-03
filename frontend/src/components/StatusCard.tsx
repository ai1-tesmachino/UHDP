interface Props {
    label: string;
    value: string | number;
    detail?: string;
}

export default function StatusCard({
    label,
    value,
    detail,
}: Props) {
    return (
        <div className="status-card">
            <div className="status-card-label">
                {label}
            </div>

            <div className="status-card-value">
                {value}
            </div>

            {detail && (
                <div className="status-card-detail">
                    {detail}
                </div>
            )}
        </div>
    );
}