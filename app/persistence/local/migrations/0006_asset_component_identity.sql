CREATE TABLE assets (
    asset_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE hardware_components (
    component_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    category TEXT NOT NULL,
    identity_key TEXT NOT NULL,
    legacy_device_id TEXT,
    identity_basis TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (asset_id, component_id),
    UNIQUE (asset_id, identity_key)
);

CREATE INDEX hardware_components_asset_category_idx
    ON hardware_components (asset_id, category);

CREATE TABLE session_asset_links (
    session_id TEXT PRIMARY KEY REFERENCES qc_sessions(session_id),
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    UNIQUE (session_id, asset_id)
);

CREATE TABLE diagnostic_run_identities (
    run_id TEXT PRIMARY KEY REFERENCES diagnostic_runs(run_id),
    session_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    component_id TEXT,
    FOREIGN KEY (session_id, asset_id)
        REFERENCES session_asset_links(session_id, asset_id),
    FOREIGN KEY (asset_id, component_id)
        REFERENCES hardware_components(asset_id, component_id)
);

CREATE INDEX diagnostic_run_identities_asset_idx
    ON diagnostic_run_identities (asset_id, session_id);

CREATE TRIGGER diagnostic_run_identity_owner_insert
BEFORE INSERT ON diagnostic_run_identities
WHEN NOT EXISTS (
    SELECT 1
    FROM diagnostic_runs
    WHERE diagnostic_runs.run_id = NEW.run_id
      AND diagnostic_runs.session_id = NEW.session_id
)
BEGIN
    SELECT RAISE(ABORT, 'diagnostic run does not belong to the supplied session');
END;

CREATE TRIGGER diagnostic_run_identity_owner_update
BEFORE UPDATE OF run_id, session_id, asset_id, component_id
ON diagnostic_run_identities
WHEN NOT EXISTS (
    SELECT 1
    FROM diagnostic_runs
    WHERE diagnostic_runs.run_id = NEW.run_id
      AND diagnostic_runs.session_id = NEW.session_id
)
BEGIN
    SELECT RAISE(ABORT, 'diagnostic run does not belong to the supplied session');
END;

CREATE TRIGGER diagnostic_run_session_immutable
BEFORE UPDATE OF session_id ON diagnostic_runs
WHEN NEW.session_id != OLD.session_id
 AND EXISTS (
    SELECT 1
    FROM diagnostic_run_identities
    WHERE run_id = OLD.run_id
)
BEGIN
    SELECT RAISE(ABORT, 'diagnostic run ownership cannot be changed');
END;

CREATE TRIGGER session_asset_immutable
BEFORE UPDATE OF asset_id ON session_asset_links
WHEN NEW.asset_id != OLD.asset_id
BEGIN
    SELECT RAISE(ABORT, 'QC session asset ownership cannot be changed');
END;

CREATE TRIGGER evidence_run_session_owner_insert
BEFORE INSERT ON evidence
WHEN NEW.run_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1
    FROM diagnostic_runs
    WHERE diagnostic_runs.run_id = NEW.run_id
      AND diagnostic_runs.session_id = NEW.session_id
)
BEGIN
    SELECT RAISE(ABORT, 'evidence run does not belong to the supplied session');
END;

CREATE TRIGGER evidence_run_session_owner_update
BEFORE UPDATE OF run_id, session_id ON evidence
WHEN NEW.run_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1
    FROM diagnostic_runs
    WHERE diagnostic_runs.run_id = NEW.run_id
      AND diagnostic_runs.session_id = NEW.session_id
)
BEGIN
    SELECT RAISE(ABORT, 'evidence run does not belong to the supplied session');
END;
