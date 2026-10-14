#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${EUID}" -eq 0 ]]; then
    echo "Run this script as your normal user; it will use sudo only for apt packages." >&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "This installer requires apt (Debian and Debian-derived Linux)." >&2
    exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required to install operating-system packages." >&2
    exit 1
fi

sudo -v
sudo apt-get update

APT_PACKAGES=(
    acpi
    alsa-utils
    build-essential
    ca-certificates
    bluez
    dmidecode
    dnsutils
    edid-decode
    ethtool
    evtest
    fio
    fwupd
    glmark2
    intel-gpu-tools
    iproute2
    iputils-ping
    iperf3
    iw
    lshw
    libasound2-dev
    libevdev-dev
    libudev-dev
    libusb-1.0-0
    lm-sensors
    libinput-tools
    memtester
    mesa-utils
    nodejs
    nvtop
    npm
    nvme-cli
    pipewire
    pciutils
    pkg-config
    python3
    python3-dev
    python3-evdev
    python3-pip
    python3-pyudev
    python3-usb
    python3-venv
    rfkill
    smartmontools
    sysstat
    stress-ng
    tpm2-tools
    usbutils
    util-linux
    upower
    v4l-utils
    vulkan-tools
    wireplumber
    x11-xserver-utils
    xdg-utils
)

if apt-cache show chromium >/dev/null 2>&1; then
    APT_PACKAGES+=(chromium)
elif apt-cache show firefox-esr >/dev/null 2>&1; then
    APT_PACKAGES+=(firefox-esr)
elif apt-cache show firefox >/dev/null 2>&1; then
    APT_PACKAGES+=(firefox)
else
    echo "No supported browser package found (tried chromium, firefox-esr, firefox)." >&2
    exit 1
fi

sudo apt-get install -y --no-install-recommends "${APT_PACKAGES[@]}"

python3 - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit(
        f"UHDP requires Python 3.10 or newer; found {sys.version.split()[0]}."
    )
PY

node <<'JS'
const [major, minor] = process.versions.node.split(".").map(Number);
const supported =
  major > 22 ||
  (major === 22 && minor >= 12) ||
  (major === 20 && minor >= 19);
if (!supported) {
  console.error(
    `UHDP frontend requires Node.js 20.19+ or 22.12+; found ${process.versions.node}.`
  );
  process.exit(1);
}
JS

cd "$ROOT_DIR"
python3 -m venv .venv
".venv/bin/python" -m pip install --upgrade pip
".venv/bin/python" -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created .env from .env.example."
fi

npm --prefix frontend ci
npm --prefix frontend run build

mkdir -p data/reports data/sessions

cat <<'EOF'

UHDP installation is ready.

Start the application as your normal user:
  bash ./scripts/run_uhdp_linux.sh

Then open:
  http://127.0.0.1:3000/

The installed tools are available on the OS, but UHDP only runs diagnostics
that have been explicitly integrated. Storage benchmark tools such as fio are
not run automatically.
EOF
