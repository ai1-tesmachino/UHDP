CREATE TABLE storage_benchmarks (
    benchmark_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    mountpoint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('Running', 'Completed', 'Interrupted', 'Failed')
    ),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    payload_json TEXT NOT NULL
);

CREATE INDEX storage_benchmarks_device_started_idx
    ON storage_benchmarks (device_id, started_at);

CREATE UNIQUE INDEX one_storage_benchmark_per_mount_idx
    ON storage_benchmarks (mountpoint) WHERE status = 'Running';
