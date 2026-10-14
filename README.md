# UHDP Phase 1 Production Starter

cd C:\Projects\UHDP_Phase1_Production
.\.venv\Scripts\activate

uvicorn app.main:app --reload

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

## Supabase persistence

File storage remains the default. To use Supabase, apply
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