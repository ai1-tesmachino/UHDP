#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_PARENT="${UHDP_LIVE_BUILD_PARENT:-${TMPDIR:-/tmp}}"
OUTPUT_DIR="${UHDP_LIVE_OUTPUT_DIR:-${ROOT_DIR}/../uhdp-live-output}"

die() {
    printf '[UHDP Live build] ERROR: %s\n' "$*" >&2
    exit 1
}

[[ "$(uname -s)" == "Linux" ]] || die "Build this ISO on Linux; cross-building native Python wheels is not supported."
[[ "$(uname -m)" == "x86_64" ]] || die "The initial image target is amd64; build on an x86_64 host."
[[ "${EUID}" -eq 0 ]] || die "Run with sudo on a dedicated Debian 13 (trixie) build host."
. /etc/os-release
[[ "${ID:-}" == "debian" && "${VERSION_CODENAME:-}" == "trixie" ]] \
    || die "Build on Debian 13 (trixie) to match the target image."
command -v lb >/dev/null 2>&1 || die "Install Debian live-build on the build host."
command -v npm >/dev/null 2>&1 || die "Install Node.js and npm on the build host."
[[ -d "$ROOT_DIR/frontend/node_modules" ]] || die "Frontend dependencies are missing; run npm ci in frontend/ before building."

mkdir -p "$OUTPUT_DIR"
[[ -w "$OUTPUT_DIR" ]] || die "ISO output directory is not writable: $OUTPUT_DIR"

BUILD_DIR="$(mktemp -d "${BUILD_PARENT%/}/uhdp-live-build.XXXXXX")"
printf '[UHDP Live build] Working directory: %s\n' "$BUILD_DIR"
printf '[UHDP Live build] ISO output directory: %s\n' "$OUTPUT_DIR"

npm --prefix "$ROOT_DIR/frontend" run build

mkdir -p \
    "$BUILD_DIR/config/package-lists" \
    "$BUILD_DIR/config/hooks/normal" \
    "$BUILD_DIR/config/includes.chroot/etc/xdg/autostart" \
    "$BUILD_DIR/config/includes.chroot/opt/uhdp"
cp "$ROOT_DIR/packaging/live-build/config/package-lists/uhdp.list.chroot" \
    "$BUILD_DIR/config/package-lists/"
cp "$ROOT_DIR/packaging/live-build/config/hooks/normal/0100-uhdp-runtime.hook.chroot" \
    "$BUILD_DIR/config/hooks/normal/"
chmod 0755 "$BUILD_DIR/config/hooks/normal/0100-uhdp-runtime.hook.chroot"
cp "$ROOT_DIR/packaging/live-build/config/includes.chroot/etc/xdg/autostart/uhdp-live.desktop" \
    "$BUILD_DIR/config/includes.chroot/etc/xdg/autostart/"
tar -C "$ROOT_DIR" --exclude='__pycache__' --exclude='*.pyc' -cf - app profiles \
    | tar -C "$BUILD_DIR/config/includes.chroot/opt/uhdp/" -xf -
cp "$ROOT_DIR/requirements.txt" "$BUILD_DIR/config/includes.chroot/opt/uhdp/"
mkdir -p "$BUILD_DIR/config/includes.chroot/opt/uhdp/frontend/dist"
cp -a "$ROOT_DIR/frontend/dist/." "$BUILD_DIR/config/includes.chroot/opt/uhdp/frontend/dist/"
mkdir -p "$BUILD_DIR/config/includes.chroot/opt/uhdp/scripts"
cp "$ROOT_DIR/scripts/run_uhdp_live.sh" \
    "$ROOT_DIR/scripts/provision_local_supervisor_credential.py" \
    "$ROOT_DIR/scripts/serve_uhdp_ui.py" \
    "$BUILD_DIR/config/includes.chroot/opt/uhdp/scripts/"
chmod 0755 "$BUILD_DIR/config/includes.chroot/opt/uhdp/scripts/run_uhdp_live.sh"

cd "$BUILD_DIR"
lb config \
    --mode debian \
    --distribution trixie \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --archive-areas "main contrib non-free-firmware" \
    --bootappend-live "boot=live components" \
    --debian-installer false \
    --memtest none \
    --iso-application UHDP \
    --iso-publisher UHDP \
    --iso-volume UHDP_LIVE
lb build

shopt -s nullglob
images=("$BUILD_DIR"/*.iso)
[[ "${#images[@]}" -eq 1 ]] || die "Expected one ISO build artifact; found ${#images[@]}."
output_path="${OUTPUT_DIR}/$(basename "${images[0]}")"
[[ ! -e "$output_path" ]] || die "Refusing to overwrite an existing ISO: $output_path"
cp -- "${images[0]}" "$output_path"
printf '[UHDP Live build] ISO created: %s\n' "$output_path"
printf '[UHDP Live build] Build workspace retained for inspection: %s\n' "$BUILD_DIR"
