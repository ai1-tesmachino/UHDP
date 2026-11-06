# UHDP Debian Live USB (initial packaging slice)

This packaging path is separate from `scripts/install_linux.sh` and
`scripts/run_uhdp_linux.sh`; those installed-system scripts remain unchanged.
The first image target is Debian 13 (trixie), amd64, XFCE, and Firefox ESR.
The ISO build requires network access to Debian repositories and Python
package indexes. Once built, the application, Python environment, browser, and
React assets are on the image; the technician UI does not use npm, Vite, a CDN,
or internet access at boot.

## Build

Use a dedicated Debian 13 amd64 build host with `live-build`, Python 3, Node.js,
npm, and root privileges. From a clean UHDP checkout:

```bash
sudo apt-get update
sudo apt-get install -y live-build python3 nodejs npm
cd /path/to/UHDP
npm --prefix frontend ci
sudo --preserve-env=TMPDIR bash scripts/build_uhdp_live_iso.sh
```

The script builds the frontend and a Live ISO in
`../uhdp-live-output/`. Set `UHDP_LIVE_OUTPUT_DIR` or
`UHDP_LIVE_BUILD_PARENT` to choose other locations. Its uniquely named
live-build workspace is retained for inspection. This initial build recipe
targets x86_64/amd64 only; Secure Boot, legacy BIOS, and non-amd64 boot
compatibility have not yet been validated.

## Persistent data partition

The image does **not** format, repartition, or automatically mount computer
disks. Before relying on the USB, create a separate ext4 partition on the
intended removable UHDP USB and give it the unique filesystem label
`UHDP_DATA`. Creating a filesystem erases the selected partition: identify the
USB device by its stable `/dev/disk/by-id/usb-*` path and verify its model,
serial, and size before any manual partitioning or formatting. Do not select
the inspected computer's internal disk. Do not run a format command as part
of normal UHDP launch.

After creating and verifying the partition, set up its data directory and
ownership for the live desktop user. For example, after the desktop mounts the
labelled partition at `/media/$USER/UHDP_DATA`:

```bash
sudo mkdir -p "/media/$USER/UHDP_DATA/uhdp-data"
sudo chown "$(id -u):$(id -g)" "/media/$USER/UHDP_DATA/uhdp-data"
```

Confirm the mount source is the intended removable USB partition before
running these commands. On startup UHDP resolves only
`/dev/disk/by-label/UHDP_DATA`, requires ext4, verifies a removable-device
ancestor, mounts that partition through UDisks if needed using `nodev,nosuid,
noexec`, and refuses to start if the persistent directory is absent or
unwritable. It does not search for or mount other partitions. A duplicate
label, a device not reported removable by the kernel, or unsupported USB
hardware fails closed; no report is written to the ephemeral live root.

Before starting the API, the Live launcher selects SQLite and runs the
idempotent legacy importer against `UHDP_DATA/uhdp-data/sessions` and
`UHDP_DATA/uhdp-data/reports`. The persistent
`UHDP_DATA/uhdp-data/uhdp.sqlite3` database is the canonical store for new
sessions, asset identities, reports, and reopen audit events. Existing JSON
files are imported only when their records are absent and are retained as
legacy files; normal SQLite-backed writes do not update those JSON files.
Rendered report revision snapshots are stored under
`UHDP_DATA/uhdp-data/Reports`, and application logs remain under
`UHDP_DATA/uhdp-data/logs`. No second asset store or schema migration is
introduced by Live startup. Cloud authentication and synchronization remain
separate product work.

The local supervisor credential is provisioned after the Live launcher mounts
the data partition. Provisioning refuses to replace an existing credential by
default. Credential rotation requires `--rotate` and the exact confirmation
`ROTATE`; the new hash is written atomically with restrictive file permissions.

## Boot and acceptance checks

Write the ISO to the intended USB using a trusted imaging utility, then boot a
reference amd64 laptop in the graphical Live environment. Do not install an OS
to the inspected laptop. Confirm:

1. The UHDP autostart window explains any startup failure and reaches the
   technician UI without network access.
2. `curl --fail http://127.0.0.1:8000/health/` returns `{"status":"healthy",...}`
   and `curl --fail http://127.0.0.1:3000/` returns the bundled application.
3. `ss -ltnp` shows both application listeners bound to `127.0.0.1`, not
   `0.0.0.0` or a LAN address.
4. With no correctly labelled removable ext4 partition, UHDP refuses to start
   and no session/report directory is created on the live root.
5. With the prepared `UHDP_DATA` partition, create a session and report, shut
   down, reboot from USB, and verify the report JSON, session JSON, and log
   remain on that partition and are still readable.
6. Verify the target laptop's internal partitions were neither mounted nor
   modified by boot or UHDP launch.
7. Repeat the checks with networking disabled. Report actual model, BIOS/UEFI
   mode, kernel, graphics/network drivers, ISO checksum, and observed outcome.

The build script and launcher have not been run on Linux or validated on
physical hardware in this change. Debian Live boot, UDisks policy behavior,
removable-device reporting, browser kiosk startup, and reboot persistence
remain mandatory Linux-host acceptance tests.

## Rollback

The Live packaging files and build workspace are separate from the existing
installer/launcher. To roll back, stop using the generated ISO and remove only
the explicitly identified Live build workspace/output artifact after
confirming its exact path. The installed-system launch flow is unchanged.
