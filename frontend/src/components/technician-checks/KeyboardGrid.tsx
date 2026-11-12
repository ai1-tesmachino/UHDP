import type { KeyboardKey } from "../../technicianChecks/technicianCheckModels";

export function KeyboardGrid({
    rows,
    tested,
    faulty,
    selected,
    disabled = false,
    onSelect,
}: {
    rows: KeyboardKey[][];
    tested: string[];
    faulty: string[];
    selected: string | null;
    disabled?: boolean;
    onSelect(code: string): void;
}) {
    return (
        <div className="keyboard-test-layout" aria-label="US QWERTY keyboard">
            {rows.map((row, rowIndex) => (
                <div className="keyboard-test-row" key={`row-${rowIndex}`}>
                    {row.map((key) => {
                        const isTested = tested.includes(key.code);
                        const isFaulty = faulty.includes(key.code);
                        const isSelected = selected === key.code;
                        return (
                            <button
                                className={[
                                    "keyboard-test-key",
                                    key.width ? `is-${key.width}` : "",
                                    isTested ? "is-tested" : "",
                                    isFaulty ? "is-faulty" : "",
                                    isSelected ? "is-selected" : "",
                                ].filter(Boolean).join(" ")}
                                key={key.code}
                                type="button"
                                disabled={disabled}
                                aria-pressed={isSelected}
                                aria-label={`${key.label}${isFaulty ? ", marked faulty" : ""}${isTested ? ", key response detected" : ""}`}
                                onClick={() => onSelect(key.code)}
                            >
                                {key.label}
                            </button>
                        );
                    })}
                </div>
            ))}
        </div>
    );
}
