# Standalone Linux diagnostics

## Target

The installation scripts target Debian-based lightweight Linux systems. For a
bootable inspection USB, use a lightweight Debian Live desktop (for example,
XFCE) so the technician has a browser and graphical session without installing
an OS on the inspected laptop. The scripts install UHDP and its dependencies on
an existing Linux installation; they do not create a bootable ISO.

## Install and launch

From the UHDP repository directory, run as the regular technician account:

```bash
bash ./scripts/install_linux.sh
bash ./scripts/run_uhdp_linux.sh
```

The installer requests `sudo` only for apt packages, creates the Python
environment in `.venv`, installs `requirements.txt`, installs the frontend from
its locked npm manifest, and creates a production frontend build. It preserves
an existing `.env`; if none exists, it copies `.env.example`.

Open `http://127.0.0.1:3000/`. The runner binds the API and frontend to
loopback and stops both when you press Ctrl+C. A graphical desktop must already
be available; the installer intentionally does not install a full desktop
environment.

## Test engines in the current application

`requirements.txt` installs the pinned Python dependencies (including FastAPI,
Uvicorn, APScheduler, Pydantic, and `psutil`). The installer also provides
Node.js/npm for building the React/Vite UI and native Linux utilities requested
for inventory and optional diagnostics: `pciutils`, `usbutils`, `dmidecode`,
`util-linux`, `smartmontools`, `nvme-cli`, `fio`, `stress-ng`, `memtester`,
`lm-sensors`, `upower`, `acpi`, `sysstat`, `python3-evdev`, `evtest`,
`libinput-tools`, `v4l-utils`, `alsa-utils`, `pipewire`, `wireplumber`, `bluez`,
`iw`, `rfkill`, `iproute2`, `ethtool`, `iperf3`, `xrandr`, `edid-decode`,
`mesa-utils`, `glmark2`, `vulkan-tools`, `intel-gpu-tools`, `nvtop`, `fwupd`,
`tpm2-tools`, `pyudev`, and `python3-usb`. It also installs compiler and
development headers to support Python hardware packages, plus Chromium where
available (otherwise Firefox ESR/Firefox) for the technician UI and
browser-based media/manual checks.

The current Linux storage discovery calls `smartctl --json --all` read-only per
physical disk when `smartctl` is available. A reported SMART failure is exposed
as a failure; absent SMART data, unsupported devices, and permission errors
remain unknown or blocked instead of passing. Webcam discovery queries at most
four `/dev/video*` nodes with `v4l2-ctl --all`; actual image quality is still
confirmed by the guided live-preview test. Display discovery uses DRM modes and
reads the active refresh rate from `xrandr` when an X display is available.
`fio`, `memtester`, `stress-ng`, and GPU benchmark tools are installed but are
not automatically run against internal drives or without an explicit test
integration.

The capability catalog lists additional possible engines (such as `smartctl`,
`fio`, `glmark2`, `iperf3`, `v4l2`, and audio/Bluetooth libraries). Listing or
detecting one of these tools does **not** mean UHDP currently runs every test
that tool could support. A test must be explicitly integrated and return
measured evidence before its result can be presented as a pass.

## Linux coverage status

| Area | Current Linux data or checks | Not yet covered by the current implementation |
|---|---|---|
| CPU | Identity, cores, frequency/utilization via `psutil`; bounded CPU load | Standardized benchmark scores and complete thermal/throttle analysis |
| RAM | Capacity/use via `psutil`; optional module inventory with `lshw`; bounded in-OS readback | Full physical-memory coverage, comprehensive SPD details and error diagnosis |
| Storage | Mounted-volume use via `psutil`; physical block identity/capacity/serial/firmware from sysfs; read-only SMART/NVMe health query when `smartctl` is installed and permitted | Safe performance benchmarks; SMART access may be blocked by OS permissions |
| GPU | DRM identity, driver and exposed VRAM inventory | Standardized rendering/benchmark/stability and temperature testing |
| Battery | Linux power-supply status, exposed capacity, cycles, voltage/current and wear estimate | Adapter identification and reliable health telemetry on systems that do not expose it |
| Display/system/board | DRM connectors and supported modes; active refresh rate via `xrandr` when available; DMI system and motherboard identity | TPM/Secure Boot policy checks and complete firmware inventory |
| Wi-Fi, Bluetooth, camera, keyboard, audio, USB | Capability/device-node inventory through `/sys`, `/proc`, `/dev` and `pyudev`; guided browser/manual checks | Automated connectivity/throughput, pairing, capture/format, insertion/removal and per-port capability tests |
| Cooling/sensors | `psutil` readings when the platform exposes them | Reliable fan RPM, thermal trends and response analysis across laptop vendors |
| Manual checks | Guided technician outcomes and browser-based speaker, microphone and camera interaction | OEM-specific checks and automatic mapping of every absent component to N/A |

Missing hardware should be recorded as not applicable; unavailable test
instrumentation should be blocked or not run. Neither condition is a failure.
The live image must not start write benchmarks against internal or
technician-owned storage by default.

## Live USB packaging

The live image should include only the desktop/browser, Python runtime, UHDP,
and the native diagnostic tools needed by implemented tests. Optional tools
should be visible as unavailable until their test integration is complete.
The installation scripts are a preparation step, not a live-image build
recipe. Boot-time kiosk startup and a hardware validation matrix are still
needed before calling a USB image production-ready.
