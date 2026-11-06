import { useEffect, useId, useState } from "react";

import { getDiagnosticSessions } from "../api/execution";
import type { AssetResolutionSelection } from "../api/execution";

interface Props {
    value: AssetResolutionSelection | null;
    onChange: (selection: AssetResolutionSelection) => void;
    disabled?: boolean;
}

export default function AssetResolutionPicker({ value, onChange, disabled = false }: Props) {
    const [knownAssetIds, setKnownAssetIds] = useState<string[]>([]);
    const [lookupUnavailable, setLookupUnavailable] = useState(false);
    const id = useId();

    useEffect(() => {
        let current = true;
        getDiagnosticSessions()
            .then((sessions) => {
                if (!current) return;
                setKnownAssetIds([
                    ...new Set(
                        sessions
                            .map((session) => session.asset_id)
                            .filter((assetId): assetId is string => Boolean(assetId)),
                    ),
                ].sort());
            })
            .catch(() => {
                if (current) setLookupUnavailable(true);
            });
        return () => {
            current = false;
        };
    }, []);

    const assetListId = `known-assets-${id}`;
    return (
        <fieldset className="asset-resolution-picker" disabled={disabled}>
            <legend>Asset identity</legend>
            <label className="asset-resolution-choice">
                <input
                    type="radio"
                    name={`asset-resolution-${id}`}
                    checked={value?.mode === "existing"}
                    onChange={() => onChange({ mode: "existing", assetId: "" })}
                />
                Link an existing asset
            </label>
            {value?.mode === "existing" && (
                <label className="asset-resolution-detail">
                    Existing asset ID
                    <input
                        list={assetListId}
                        value={value.assetId}
                        onChange={(event) => onChange({ mode: "existing", assetId: event.target.value })}
                        autoComplete="off"
                    />
                    <datalist id={assetListId}>
                        {knownAssetIds.map((assetId) => <option value={assetId} key={assetId} />)}
                    </datalist>
                    <span>
                        The backend will verify this exact ID before linking the session.
                        {lookupUnavailable
                            ? " Known IDs could not be loaded; you can still enter an ID to verify."
                            : knownAssetIds.length
                              ? ` ${knownAssetIds.length} known asset ${knownAssetIds.length === 1 ? "ID is" : "IDs are"} available as suggestions.`
                              : " No known asset IDs are available yet."}
                    </span>
                </label>
            )}
            <label className="asset-resolution-choice">
                <input
                    type="radio"
                    name={`asset-resolution-${id}`}
                    checked={value?.mode === "new"}
                    onChange={() => onChange({ mode: "new" })}
                />
                Create a new asset
            </label>
            <label className="asset-resolution-choice">
                <input
                    type="radio"
                    name={`asset-resolution-${id}`}
                    checked={value?.mode === "unresolved"}
                    onChange={() => onChange({ mode: "unresolved" })}
                />
                Continue without asset identification
            </label>
            {value?.mode === "unresolved" && (
                <p className="warning-box" role="status">
                    This QC session will remain unresolved and will not be associated with an identified asset.
                </p>
            )}
        </fieldset>
    );
}
