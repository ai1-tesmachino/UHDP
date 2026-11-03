CREATE TABLE boot_sessions (
    boot_session_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    software_version TEXT NOT NULL,
    schema_version INTEGER NOT NULL
);

CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    company_id TEXT,
    payload_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE qc_sessions (
    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id),
    boot_session_id TEXT NOT NULL REFERENCES boot_sessions(boot_session_id),
    device_id TEXT,
    company_id TEXT,
    station_id TEXT,
    identity_snapshot_json TEXT NOT NULL,
    software_version TEXT NOT NULL,
    catalogue_version TEXT,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX qc_sessions_device_created_idx
    ON qc_sessions (device_id, created_at);

CREATE TABLE diagnostic_runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES qc_sessions(session_id),
    parent_run_id TEXT,
    diagnostic_type TEXT NOT NULL,
    device_id TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX diagnostic_runs_session_created_idx
    ON diagnostic_runs (session_id, created_at);

CREATE TABLE diagnostic_results (
    result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES diagnostic_runs(run_id),
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES qc_sessions(session_id),
    run_id TEXT REFERENCES diagnostic_runs(run_id),
    relative_path TEXT NOT NULL UNIQUE,
    original_filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    sync_state TEXT NOT NULL DEFAULT 'Pending'
        CHECK (sync_state IN ('Pending', 'Syncing', 'Synced', 'Needs attention'))
);

CREATE INDEX evidence_session_created_idx ON evidence (session_id, created_at);

CREATE TABLE audit_events (
    audit_event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_snapshot_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX audit_events_entity_created_idx
    ON audit_events (entity_type, entity_id, created_at);
