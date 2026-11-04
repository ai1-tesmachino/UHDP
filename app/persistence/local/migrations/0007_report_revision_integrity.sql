ALTER TABLE report_revisions
    ADD COLUMN finalized_at TEXT;

ALTER TABLE report_revisions
    ADD COLUMN finalized_by TEXT;

ALTER TABLE report_revisions
    ADD COLUMN supersedes_revision_id TEXT
    REFERENCES report_revisions(revision_id);

ALTER TABLE report_revisions
    ADD COLUMN supersession_reason TEXT;

CREATE TRIGGER report_revision_payload_immutable
BEFORE UPDATE OF
    revision_id,
    report_id,
    revision,
    created_at,
    payload_json,
    payload_html,
    supersedes_revision_id,
    supersession_reason
ON report_revisions
BEGIN
    SELECT RAISE(ABORT, 'report revisions are immutable');
END;

CREATE TRIGGER report_revision_finalize_once
BEFORE UPDATE OF finalized_at ON report_revisions
WHEN OLD.finalized_at IS NOT NULL OR NEW.finalized_at IS NULL
BEGIN
    SELECT RAISE(ABORT, 'a finalized report revision is immutable');
END;

CREATE TRIGGER report_revision_finalizer_immutable
BEFORE UPDATE OF finalized_by ON report_revisions
WHEN OLD.finalized_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'a finalized report revision is immutable');
END;

CREATE TRIGGER report_revision_no_delete
BEFORE DELETE ON report_revisions
BEGIN
    SELECT RAISE(ABORT, 'report revisions cannot be deleted');
END;
