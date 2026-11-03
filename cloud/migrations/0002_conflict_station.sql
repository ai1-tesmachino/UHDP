ALTER TABLE sync_conflicts
    ADD COLUMN station_id TEXT REFERENCES stations(station_id);

UPDATE sync_conflicts AS conflicts
SET station_id = sessions.station_id
FROM qc_sessions AS sessions
WHERE sessions.company_id = conflicts.company_id
  AND sessions.session_id = conflicts.session_id
  AND conflicts.station_id IS NULL;

ALTER TABLE sync_conflicts
    ALTER COLUMN station_id SET NOT NULL;

UPDATE roles
SET permissions = permissions ||
    '["stations:read","evidence:read","analytics:read"]'::jsonb
WHERE role_id = 'administrator';
