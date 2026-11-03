CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE session_revisions (
    revision_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    revision INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (session_id, revision)
);

CREATE TABLE reports (
    report_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    payload_html TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE report_revisions (
    revision_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(report_id),
    revision INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_html TEXT,
    UNIQUE (report_id, revision)
);

CREATE TABLE outbox_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN ('Pending', 'Syncing', 'Synced', 'Needs attention')
    ),
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    last_error TEXT,
    synced_at TEXT
);

CREATE INDEX outbox_events_state_created_idx
    ON outbox_events (state, created_at);

CREATE INDEX session_revisions_session_idx
    ON session_revisions (session_id, revision);

CREATE INDEX report_revisions_report_idx
    ON report_revisions (report_id, revision);
