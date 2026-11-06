# UHDP Phase 1 Production Starter

## Development on Ubuntu

From the repository root, create and activate a Python environment, then
install backend dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --no-proxy-headers
```

In another terminal, start the frontend:

```bash
cd frontend
npm ci
npm run dev
```

Run the backend tests from the repository root with the virtual environment
active:

```bash
python -m pytest -c app/pytest.ini tests -v
```

See [docs/RUNNING_THE_APPLICATION.md](docs/RUNNING_THE_APPLICATION.md) for
installation, configuration, and local development details.

## Linux installation

On a Debian-based Linux system with a graphical desktop, run from the
repository directory as your regular user:

```bash
bash ./scripts/install_linux.sh
bash ./scripts/run_uhdp_linux.sh
```

The installer installs OS-level diagnostic utilities and Python/frontend
dependencies, then builds the UI. It requires `sudo` for apt packages and
preserves an existing `.env`. Open `http://127.0.0.1:3000/` after launch.
See [docs/LINUX_STANDALONE.md](docs/LINUX_STANDALONE.md) for package scope and
the distinction between installed utilities and integrated tests.

The separate Debian Live USB packaging path is under development and is not
yet validated on Linux hardware. See
[docs/LINUX_LIVE_USB.md](docs/LINUX_LIVE_USB.md) for its build and persistence
design. The Live image path does not replace the installed-system scripts.

## Local SQLite persistence

The Linux launcher uses a versioned SQLite database for sessions, reports,
immutable snapshots, and transactional outbox events. The first launch
idempotently imports existing local JSON sessions/reports and keeps the source
files; historical records are not queued for cloud sync. To continue explicitly
using legacy file storage set `STORAGE_BACKEND=file`. SQLite uses:

```dotenv
STORAGE_BACKEND=sqlite
```

The default path is `${DATA_DIR}/uhdp.sqlite3` (override with
`SQLITE_DATABASE_PATH`). If `REPORTS_DIRECTORY` or `SESSIONS_DIRECTORY` is
unset, it is derived from `DATA_DIR`; explicitly configured paths take
precedence. The normal Ubuntu launcher also imports legacy JSON files from the
repository's `data/reports`, `data/sessions`, and `reports` directories without
changing the originals. The database directory must be on persistent storage.

For a direct development launch that bypasses the Linux launcher, stop UHDP,
then import before switching the repository configuration:

```bash
. .venv/bin/activate
python -m app.persistence.local.import_legacy
```

The importer preserves the JSON files, skips IDs already present in SQLite, and
does not queue historical records for cloud sync. Set `SESSIONS_DIRECTORY`,
`REPORTS_DIRECTORY`, and (if needed) repeat `--reports <directory>` for any
additional report location. Existing Supabase data is not migrated. New
outbox events remain Pending until valid station credentials and a cloud
endpoint are configured; local saving is independent of connectivity.

## Supabase persistence

The legacy file backend remains available. To use Supabase, apply
`supabase/migrations/20261014000000_create_uhdp_records.sql` to the project,
then set these values in the backend `.env`:

```dotenv
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-server-only-service-role-key
SUPABASE_RECORDS_TABLE=uhdp_records
```

The backend connects to Supabase's PostgREST API using the service-role key.
Keep that key exclusively on the backend; do not add it to `frontend/.env` or
client-side code. Choosing Supabase without both required credentials raises a
configuration error rather than silently falling back to local files. Existing
file-backed profiles and operational data are not migrated automatically.