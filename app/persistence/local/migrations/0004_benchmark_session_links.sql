ALTER TABLE storage_benchmarks ADD COLUMN session_id TEXT;

CREATE INDEX storage_benchmarks_session_started_idx
    ON storage_benchmarks (session_id, started_at);
