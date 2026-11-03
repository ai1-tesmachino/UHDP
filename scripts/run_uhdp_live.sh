#!/usr/bin/env bash
set -Eeuo pipefail

UHDP_ROOT="/opt/uhdp"
API_URL="http://127.0.0.1:8000"
UI_URL="http://127.0.0.1:3000/"
DATA_LABEL="UHDP_DATA"
backend_pid=""
frontend_pid=""
browser_pid=""

die() {
    printf '[UHDP Live] ERROR: %s\n' "$*" >&2
    exit 1
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

[[ "${EUID}" -ne 0 ]] || die "Run from the logged-in technician desktop, not as root."
[[ -d "$UHDP_ROOT" ]] || die "UHDP image files are missing: $UHDP_ROOT"
[[ -x "$UHDP_ROOT/.venv/bin/uvicorn" ]] || die "Bundled Python runtime is missing."
[[ -f "$UHDP_ROOT/frontend/dist/index.html" ]] || die "Bundled UI assets are missing."
[[ -f "$UHDP_ROOT/scripts/serve_uhdp_ui.py" ]] || die "Bundled UI server is missing."

for command_name in findmnt flock lsblk readlink udisksctl; do
    command -v "$command_name" >/dev/null 2>&1 \
        || die "Required Live image utility is missing: $command_name"
done

mapfile -t labelled_partitions < <(
    lsblk -rpn -o NAME,LABEL,TYPE \
        | awk -v label="$DATA_LABEL" '$2 == label && $3 == "part" { print $1 }'
)
[[ "${#labelled_partitions[@]}" -eq 1 ]] \
    || die "Expected exactly one partition labelled ${DATA_LABEL}; found ${#labelled_partitions[@]}."
data_device="${labelled_partitions[0]}"
[[ -b "$data_device" ]] || die "${DATA_LABEL} does not resolve to a block device."
data_link="/dev/disk/by-label/${DATA_LABEL}"
[[ -L "$data_link" && "$(readlink -f -- "$data_link")" == "$data_device" ]] \
    || die "The ${DATA_LABEL} label does not resolve uniquely to the identified partition."

filesystem="$(lsblk -no FSTYPE -- "$data_device" | tr -d '[:space:]')"
[[ "$filesystem" == "ext4" ]] || die "${DATA_LABEL} must be an ext4 data partition (found: ${filesystem:-unknown})."

block_name="$(basename -- "$data_device")"
sysfs_path="$(readlink -f -- "/sys/class/block/${block_name}")"
removable=0
while [[ "$sysfs_path" == /sys/* ]]; do
    if [[ -r "${sysfs_path}/removable" ]] \
        && [[ "$(cat "${sysfs_path}/removable")" == "1" ]]; then
        removable=1
        break
    fi
    sysfs_path="${sysfs_path%/*}"
done
[[ "$removable" -eq 1 ]] || die "${DATA_LABEL} is not confirmed as removable USB media; refusing to mount it."

mountpoint="$(findmnt -rn -S "$data_device" -o TARGET | head -n 1)"
if [[ -z "$mountpoint" ]]; then
    udisksctl mount --block-device "$data_device" --options "nodev,nosuid,noexec"
    mountpoint="$(findmnt -rn -S "$data_device" -o TARGET | head -n 1)"
fi
[[ -n "$mountpoint" ]] || die "Could not mount the identified ${DATA_LABEL} partition."

DATA_ROOT="${mountpoint}/uhdp-data"
[[ -d "$DATA_ROOT" && -w "$DATA_ROOT" ]] \
    || die "The persistent data directory is missing or not writable: ${DATA_ROOT}. Prepare it as described in docs/LINUX_LIVE_USB.md."
mkdir -p "${DATA_ROOT}/reports" "${DATA_ROOT}/sessions" "${DATA_ROOT}/logs"
[[ -w "${DATA_ROOT}/reports" && -w "${DATA_ROOT}/sessions" && -w "${DATA_ROOT}/logs" ]] \
    || die "Persistent report, session, and log directories must be writable."
exec > >(tee -a "${DATA_ROOT}/logs/boot.log") 2>&1

exec 9>"${DATA_ROOT}/.launcher.lock"
flock -n 9 || die "Another UHDP Live session is already running from this data partition."

export DATA_DIR="${DATA_ROOT}"
export REPORTS_DIRECTORY="${DATA_ROOT}/reports"
export SESSIONS_DIRECTORY="${DATA_ROOT}/sessions"

cd "$UHDP_ROOT"
"$UHDP_ROOT/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
python3 "$UHDP_ROOT/scripts/serve_uhdp_ui.py" &
frontend_pid=$!

probe() {
    "$UHDP_ROOT/.venv/bin/python" - "$1" "$2" <<'PY'
import json
import sys
from urllib.request import urlopen

url, expected = sys.argv[1:]
try:
    with urlopen(url, timeout=2) as response:
        body = response.read()
        if response.status != 200:
            raise SystemExit(1)
        if expected == "api" and json.loads(body).get("status") != "healthy":
            raise SystemExit(1)
        if expected == "ui" and b'<div id="root">' not in body:
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
        kill -0 "$pid" 2>/dev/null || die "${name} exited before becoming healthy."
        if probe "$url" "$expected"; then
            printf '[UHDP Live] %s healthy at %s\n' "$name" "$url"
            return 0
        fi
        sleep 1
    done
    die "${name} did not become healthy at ${url}."
}

wait_for_service "Backend API" "${API_URL}/health/" "api" "$backend_pid"
wait_for_service "Technician UI" "$UI_URL" "ui" "$frontend_pid"

browser="$(command -v firefox-esr || true)"
[[ -n "$browser" ]] || die "Bundled Firefox ESR is unavailable."
"$browser" --kiosk --new-window "$UI_URL" &
browser_pid=$!

printf '[UHDP Live] Ready. Persistent data: %s\n' "$DATA_ROOT"
printf '[UHDP Live] API and UI are bound to loopback only.\n'
set +e
wait -n "$backend_pid" "$frontend_pid"
service_status=$?
set -e
printf '[UHDP Live] A UHDP service exited (status %s); stopping the remaining services.\n' "$service_status"
exit "$service_status"
