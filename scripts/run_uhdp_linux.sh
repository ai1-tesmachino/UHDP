#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x .venv/bin/uvicorn || ! -f frontend/dist/index.html ]]; then
    echo "UHDP is not installed. Run bash ./scripts/install_linux.sh first." >&2
    exit 1
fi

backend_pid=""
frontend_pid=""

cleanup() {
    if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
        kill "$frontend_pid" 2>/dev/null || true
    fi
    if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
        kill "$backend_pid" 2>/dev/null || true
    fi
    [[ -z "$frontend_pid" ]] || wait "$frontend_pid" 2>/dev/null || true
    [[ -z "$backend_pid" ]] || wait "$backend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

".venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
npm --prefix frontend run preview -- --host 127.0.0.1 --port 3000 --strictPort &
frontend_pid=$!

printf 'UHDP API: http://127.0.0.1:8000\n'
printf 'UHDP UI:  http://127.0.0.1:3000/\n'
printf 'Press Ctrl+C to stop both services.\n'

wait -n "$backend_pid" "$frontend_pid"
