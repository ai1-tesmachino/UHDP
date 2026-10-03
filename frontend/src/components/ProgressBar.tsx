interface Props {
    value: number;
}

export default function ProgressBar({
    value,
}: Props) {
    const normalized = Math.min(
        100,
        Math.max(0, value)
    );

    return (
        <div className="progress-container">
            <div className="progress-track">
                <div
                    className="progress-fill"
                    style={{
                        width: `${normalized}%`,
                    }}
                />
            </div>

            <div className="progress-label">
                <span>Diagnostic progress</span>
                <span>{normalized}%</span>
            </div>
        </div>
    );
}