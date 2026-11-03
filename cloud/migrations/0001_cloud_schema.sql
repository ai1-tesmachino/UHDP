CREATE TABLE companies (
    company_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
    role_id TEXT PRIMARY KEY,
    permissions JSONB NOT NULL
);

INSERT INTO roles (role_id, permissions) VALUES
    ('administrator', '["company:manage","station:manage","stations:read","records:read","records:review","sync:write","evidence:manage","evidence:read","analytics:read"]'),
    ('supervisor', '["stations:read","records:read","records:review","evidence:read","analytics:read"]'),
    ('technician', '["stations:read","records:read","analytics:read"]'),
    ('analyst', '["records:read","analytics:read"]')
ON CONFLICT (role_id) DO NOTHING;

CREATE TABLE stations (
    station_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    name TEXT NOT NULL,
    token_sha256 TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX stations_company_idx ON stations (company_id, station_id);

CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role_id TEXT NOT NULL REFERENCES roles(role_id),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, username)
);

CREATE TABLE boot_sessions (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    boot_session_id TEXT NOT NULL,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    started_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (company_id, boot_session_id)
);

CREATE TABLE devices (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    device_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, device_id)
);

CREATE TABLE qc_sessions (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    session_id TEXT NOT NULL,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    device_id TEXT,
    latest_revision INTEGER NOT NULL,
    identity_snapshot JSONB NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    conflict_state TEXT NOT NULL DEFAULT 'clear'
        CHECK (conflict_state IN ('clear', 'needs_review')),
    PRIMARY KEY (company_id, session_id)
);

CREATE INDEX qc_sessions_company_created_idx
    ON qc_sessions (company_id, created_at DESC);

CREATE TABLE qc_session_revisions (
    revision_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    session_id TEXT NOT NULL,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    revision INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    conflict BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX qc_session_revisions_session_idx
    ON qc_session_revisions (company_id, session_id, revision);

CREATE TABLE diagnostic_runs (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    parent_run_id TEXT,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    device_id TEXT,
    diagnostic_type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (company_id, run_id)
);

CREATE TABLE diagnostic_results (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    result_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (company_id, result_id)
);

CREATE TABLE evidence_metadata (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    evidence_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    run_id TEXT,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    object_key TEXT,
    original_filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    sha256 TEXT NOT NULL,
    upload_state TEXT NOT NULL DEFAULT 'pending'
        CHECK (upload_state IN ('pending', 'uploading', 'synced', 'needs_attention')),
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (company_id, evidence_id)
);

CREATE TABLE reports (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    report_id TEXT NOT NULL,
    session_id TEXT,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (company_id, report_id)
);

CREATE TABLE report_revisions (
    revision_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    report_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    conflict BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE storage_benchmarks (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    benchmark_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (company_id, benchmark_id)
);

CREATE TABLE audit_events (
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    audit_event_id TEXT NOT NULL,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, audit_event_id)
);

CREATE TABLE sync_event_receipts (
    event_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    payload_sha256 TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sync_conflicts (
    conflict_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    session_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    existing_payload_sha256 TEXT NOT NULL,
    incoming_payload_sha256 TEXT NOT NULL,
    incoming_payload JSONB NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    review_state TEXT NOT NULL DEFAULT 'needs_review'
        CHECK (review_state IN ('needs_review', 'resolved'))
);

CREATE INDEX sync_conflicts_company_state_idx
    ON sync_conflicts (company_id, review_state, detected_at DESC);
