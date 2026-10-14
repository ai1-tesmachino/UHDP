#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="http://127.0.0.1:8000"
UI_URL="http://127.0.0.1:3000/"
DATA_ROOT="${XDG_STATE_HOME:-${HOME}/.local/state}/uhdp"
LOG_DIR="${DATA_ROOT}/logs"
AUTOSTART_FILE="${XDG_CONFIG_HOME:-${HOME}/.config}/autostart/uhdp.desktop"
START_BROWSER=1
CHECK_ONLY=0
KIOSK=1
backend_pid=""
frontend_pid=""
browser_pid=""

usage() {
    cat <<'EOF'
Usage: bash scripts/run_uhdp_linux.sh [OPTIONS]

Boot-time check, writable-data setup, service startup, health checks, and UI launch.
Run as the logged-in technician, not as root.

Options:
  --check-only          Check the installation and prepare data directories, then exit.
  --no-browser          Start and health-check UHDP without launching a browser.
  --windowed            Launch the browser normally instead of kiosk mode.
  --install-autostart   Add this launcher to the current user's desktop autostart.
  --remove-autostart    Remove this launcher's current-user desktop autostart.
  -h, --help            Show this help.

The launcher does not install packages or run diagnostics. Install/update dependencies
with scripts/install_linux.sh before deployment. Missing optional tools are reported.
EOF
}

log() {
    printf '[UHDP boot %s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*"
}

die() {
    printf '[UHDP boot] ERROR: %s\n' "$*" >&2
    exit 1
}

desktop_quote() {
    local value="$1"
    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    value="${value//%/%%}"
    printf '"%s"' "$value"
}

install_autostart() {
    [[ "${EUID}" -ne 0 ]] || die "Run autostart setup as the technician user, not root."
    local launcher
    launcher="${ROOT_DIR}/scripts/run_uhdp_linux.sh"
    mkdir -p "$(dirname "$AUTOSTART_FILE")"
    {
        printf '[Desktop Entry]\n'
        printf 'Type=Application\n'
        printf 'Name=UHDP Technician Diagnostics\n'
        printf 'Comment=Start UHDP diagnostics when the desktop starts\n'
        printf 'Exec=/usr/bin/bash %s\n' "$(desktop_quote "$launcher")"
        printf 'Terminal=false\n'
        printf 'X-GNOME-Autostart-enabled=true\n'
        printf 'OnlyShowIn=XFCE;GNOME;KDE;\n'
    } >"$AUTOSTART_FILE"
    chmod 0644 "$AUTOSTART_FILE"
    log "Desktop autostart installed: $AUTOSTART_FILE"
}

cleanup() {
    local pid
    for pid in "$browser_pid" "$frontend_pid" "$backend_pid"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    for pid in "$browser_pid" "$frontend_pid" "$backend_pid"; do
        if [[ -n "$pid" ]]; then
            wait "$pid" 2>/dev/null || true
        fi
    done
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for arg in "$@"; do
    case "$arg" in
        --check-only) CHECK_ONLY=1 ;;
        --no-browser) START_BROWSER=0 ;;
        --windowed) KIOSK=0 ;;
        --install-autostart) install_autostart; exit 0 ;;
        --remove-autostart)
            rm -f -- "$AUTOSTART_FILE"
            log "Desktop autostart removed: $AUTOSTART_FILE"
            exit 0
            ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $arg (use --help for usage)." ;;
    esac
done

[[ "${EUID}" -ne 0 ]] || die "Run as the logged-in technician user, not root."
[[ "$(uname -s)" == "Linux" ]] || die "This launcher supports Linux only."
if mkdir -p "$LOG_DIR" && [[ -w "$LOG_DIR" ]] && command -v tee >/dev/null 2>&1; then
    exec > >(tee -a "${LOG_DIR}/boot.log") 2>&1
else
    log "WARNING: could not open the persistent boot log; continuing with console output."
fi
[[ -d "$ROOT_DIR" ]] || die "UHDP installation directory is missing: $ROOT_DIR"
[[ -x "$ROOT_DIR/.venv/bin/python" ]] || die "Python environment missing. Run scripts/install_linux.sh."
[[ -x "$ROOT_DIR/.venv/bin/uvicorn" ]] || die "Uvicorn missing. Run scripts/install_linux.sh."
[[ -f "$ROOT_DIR/frontend/dist/index.html" ]] || die "Frontend build missing. Run scripts/install_linux.sh."
[[ -f "$ROOT_DIR/frontend/node_modules/vite/bin/vite.js" ]] || die "Vite preview dependency missing. Run scripts/install_linux.sh."
command -v python3 >/dev/null 2>&1 || die "python3 is required."
command -v node >/dev/null 2>&1 || die "node is required to serve the built UI."
node -e '
const [major, minor] = process.versions.node.split(".").map(Number);
if (!(major > 22 || (major === 22 && minor >= 12) || (major === 20 && minor >= 19))) {
  console.error(`UHDP requires Node.js 20.19+ or 22.12+; found ${process.versions.node}.`);
  process.exit(1);
}'

cd "$ROOT_DIR"

dotenv_value() {
    "$ROOT_DIR/.venv/bin/python" - "$1" <<'PY'
import sys
from dotenv import dotenv_values

value = dotenv_values(".env").get(sys.argv[1], "")
if value is not None:
    print(value)
PY
}

configured_data_dir="$(dotenv_value DATA_DIR)"
configured_reports_dir="$(dotenv_value REPORTS_DIRECTORY)"
configured_sessions_dir="$(dotenv_value SESSIONS_DIRECTORY)"
export DATA_DIR="${DATA_DIR:-${configured_data_dir:-$DATA_ROOT}}"
export REPORTS_DIRECTORY="${REPORTS_DIRECTORY:-${configured_reports_dir:-${DATA_DIR}/reports}}"
export SESSIONS_DIRECTORY="${SESSIONS_DIRECTORY:-${configured_sessions_dir:-${DATA_DIR}/sessions}}"
mkdir -p "$DATA_DIR" "$REPORTS_DIRECTORY" "$SESSIONS_DIRECTORY"
[[ -w "$DATA_DIR" && -w "$REPORTS_DIRECTORY" && -w "$SESSIONS_DIRECTORY" ]] \
    || die "UHDP data paths must be writable by the technician user."

command -v flock >/dev/null 2>&1 || die "flock is required (provided by util-linux)."
exec 9>"${DATA_DIR}/.boot-launcher.lock"
if ! flock -n 9; then
    log "UHDP launcher is already active for this user; leaving the existing session running."
    exit 0
fi

log "Install root: $ROOT_DIR"
log "Boot log: ${LOG_DIR}/boot.log"
log "Linux kernel: $(uname -sr); architecture: $(uname -m)"
log "Data directory: $DATA_DIR"
log "Reports directory: $REPORTS_DIRECTORY"
log "Sessions directory: $SESSIONS_DIRECTORY"

if ! "$ROOT_DIR/.venv/bin/python" -c 'import fastapi, psutil, uvicorn' >/dev/null 2>&1; then
    die "Required Python modules are unavailable. Re-run scripts/install_linux.sh."
fi
if ! "$ROOT_DIR/.venv/bin/python" -c 'import pyudev' >/dev/null 2>&1; then
    log "WARNING: pyudev is unavailable; USB inventory will use sysfs fallback."
fi

available_tools=()
missing_tools=()
for tool in lspci lsusb dmidecode smartctl nvme fio stress-ng memtester sensors \
    upower acpi evtest libinput v4l2-ctl arecord aplay bluetoothctl iw rfkill \
    ip ethtool iperf3 xrandr edid-decode glxinfo glmark2 vulkaninfo fwupdmgr \
    tpm2_getcap; do
    if command -v "$tool" >/dev/null 2>&1; then
        available_tools+=("$tool")
    else
        missing_tools+=("$tool")
    fi
done
log "Optional diagnostic utilities available: ${#available_tools[@]} of $((${#available_tools[@]} + ${#missing_tools[@]})) checked."
if ((${#missing_tools[@]})); then
    log "Optional tools not found: ${missing_tools[*]}"
fi
log "Tool availability does not mean every corresponding test is integrated or passed."
log "Internal-drive write benchmarks and stress tests will not be started by this launcher."

if ((CHECK_ONLY)); then
    log "Installation and writable data paths are ready. No services were started."
    exit 0
fi

if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    if command -v chromium >/dev/null 2>&1; then
        browser="$(command -v chromium)"
    elif command -v chromium-browser >/dev/null 2>&1; then
        browser="$(command -v chromium-browser)"
    elif command -v google-chrome >/dev/null 2>&1; then
        browser="$(command -v google-chrome)"
    elif command -v firefox-esr >/dev/null 2>&1; then
        browser="$(command -v firefox-esr)"
    elif command -v firefox >/dev/null 2>&1; then
        browser="$(command -v firefox)"
    else
        browser=""
        log "WARNING: no supported browser found; services will start without a UI window."
    fi
else
    browser=""
    log "No graphical desktop session detected; services will start headlessly."
fi

"$ROOT_DIR/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
(
    cd "$ROOT_DIR/frontend"
    exec node ./node_modules/vite/bin/vite.js preview \
        --host 127.0.0.1 --port 3000 --strictPort
) &
frontend_pid=$!

probe_url() {
    local url="$1"
    local expected="$2"
    "$ROOT_DIR/.venv/bin/python" - "$url" "$expected" <<'PY'
import json
import sys
from urllib.request import urlopen

url, expected = sys.argv[1:]
try:
    with urlopen(url, timeout=2) as response:
        body = response.read()
        if response.status != 200:
            raise SystemExit(1)
        if expected == "api":
            payload = json.loads(body)
            if payload.get("status") != "healthy":
                raise SystemExit(1)
except Exception:
    raise SystemExit(1)
PY
}

wait_for_service() {
    local name="$1"
    local url="$2"
    local expected="$3"
    local pid="$4"
    local attempt
    for attempt in $(seq 1 45); do
        if ! kill -0 "$pid" 2>/dev/null; then
            die "$name process exited before becoming healthy."
        fi
        if probe_url "$url" "$expected"; then
            log "$name healthy at $url"
            return 0
        fi
        sleep 1
    done
    die "$name failed its health check at $url."
}

log "Starting backend and frontend."
wait_for_service "Backend API" "${API_URL}/health/" "api" "$backend_pid"
wait_for_service "Frontend" "$UI_URL" "ui" "$frontend_pid"

if [[ -n "$browser" ]] && ((START_BROWSER)); then
    browser_profile="${XDG_CACHE_HOME:-${HOME}/.cache}/uhdp/browser-profile"
    mkdir -p "$browser_profile"
    if [[ "$browser" == *firefox* ]]; then
        if ((KIOSK)); then
            "$browser" --kiosk --new-window "$UI_URL" &
        else
            "$browser" --new-window "$UI_URL" &
        fi
    elif ((KIOSK)); then
        "$browser" --kiosk --no-first-run --disable-infobars \
            --user-data-dir="$browser_profile" "$UI_URL" &
    else
        "$browser" --no-first-run --user-data-dir="$browser_profile" "$UI_URL" &
    fi
    browser_pid=$!
    if ((KIOSK)); then
        log "Technician UI opened in kiosk mode with $(basename "$browser")."
    else
        log "Technician UI opened in a browser window with $(basename "$browser")."
    fi
else
    log "Technician UI: $UI_URL"
fi

log "UHDP is ready. Press Ctrl+C or end the desktop session to stop the services."
set +e
wait -n "$backend_pid" "$frontend_pid"
service_status=$?
set -e
log "A UHDP service exited (status $service_status); stopping remaining child processes."
exit "$service_status"
