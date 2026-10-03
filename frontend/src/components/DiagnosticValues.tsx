interface Props {
    diagnosticName: string;
    value: Record<string, unknown>;
}

function stringifyValue(value: unknown): string {
    if (value === null) {
        return "null";
    }

    if (value === undefined) {
        return "undefined";
    }

    if (typeof value === "object") {
        return JSON.stringify(value, null, 2) ?? String(value);
    }

    return String(value);
}

export default function DiagnosticValues({ diagnosticName, value }: Props) {
    return (
        <section className="diagnostic-value-section" aria-label={`${diagnosticName} full results`}>
            <h3>{diagnosticName.replaceAll("_", " ")}</h3>
            <table className="diagnostic-values-table">
                <tbody>
                    {Object.entries(value).map(([key, fieldValue]) => (
                        <tr key={key}>
                            <th scope="row">{key.replaceAll("_", " ")}</th>
                            <td>
                                <pre>{stringifyValue(fieldValue)}</pre>
                            </td>
                        </tr>
                    ))}
                    {Object.keys(value).length === 0 && (
                        <tr>
                            <td colSpan={2}>No result fields were returned.</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </section>
    );
}
