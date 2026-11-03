# Running UHDP locally

This guide covers installing UHDP on Ubuntu and running it locally for
development.

## Install on Ubuntu

Use an Ubuntu installation with a graphical desktop session. The installer
adds UHDP's Python, frontend, and diagnostic dependencies, builds the frontend,
and configures the app to start when your desktop user logs in. It does not
install a desktop environment.

Run these commands from a regular user account (not a root shell). Node.js
20.19+ or 22.12+ is required; the NodeSource setup below installs the Node.js
22 package so the installer's version check succeeds:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
node --version
```

Confirm the reported Node.js version is 22.12 or newer, then clone and install
the application:

```bash
git clone https://github.com/ai1-tesmachino/UHDP.git
cd UHDP
bash ./scripts/install_linux.sh
```

The installer uses `sudo` to install Ubuntu packages, creates the Python
environment, installs backend and frontend dependencies, builds the UI, and
sets up per-user desktop autostart. It preserves an existing `.env`; otherwise
it copies `.env.example`. Review `.env` before configuring optional storage.
Keep any Supabase service-role key in the backend `.env` only.

To start UHDP immediately without logging out and back in:

```bash
bash ./scripts/run_uhdp_linux.sh
```

The launcher starts the API and built UI, checks both are healthy, and opens
the UI in a browser if a graphical session is available. Open
`http://127.0.0.1:3000/` if you need to access it manually. Press `Ctrl+C` to
stop the launcher and its services. For reinstalling/updating dependencies or
removing autostart, see [LINUX_STANDALONE.md](LINUX_STANDALONE.md).

## Run from a development checkout

Use two terminal windows, both opened at the repository root
(`C:\Projects\UHDP_Phase1_Production` on Windows).

## Prerequisites

- Python and Node.js/npm installed.
- The repository's Python virtual environment and frontend dependencies
  installed. The commands below create/install them if needed.

## 1. Configure the backend

In PowerShell:

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copying `.env.example` is optional; the application has defaults for local
development. Its default storage backend is local files. If you choose
Supabase, configure its URL and service-role key in the backend `.env` only;
never put the service-role key in frontend code or environment files.

## 2. Start the backend

In the first terminal, from the repository root with the virtual environment
activated:

```powershell
uvicorn app.main:app --reload
```

The backend listens on `http://127.0.0.1:8000`. Interactive API
documentation is available at `http://127.0.0.1:8000/docs`.

## 3. Start the frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000/` in your browser. Keep both terminals running
while using the application. Stop either development server with `Ctrl+C`.

## Other useful commands

Build the frontend for production from the `frontend` directory:

```powershell
npm run build
```

Run the backend tests from the repository root with the virtual environment
activated:

```powershell
pytest
```

The supplied `docker-compose.yml` runs the backend container only; it does not
start the frontend.
