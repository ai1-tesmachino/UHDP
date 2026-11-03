import os
import pathlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


if os.name == "nt":
    _original_symlink_to = pathlib.Path.symlink_to

    def _safe_windows_symlink_to(self, target, target_is_directory=False):
        try:
            return _original_symlink_to(self, target, target_is_directory)
        except OSError as exc:
            if getattr(exc, "winerror", None) != 1314:
                raise

            target_path = pathlib.Path(target)
            if target_is_directory or target_path.is_dir():
                subprocess.run(
                    [
                        "cmd",
                        "/c",
                        "mklink",
                        "/J",
                        str(self),
                        str(target_path),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return None

            try:
                os.link(target_path, self)
            except OSError:
                raise exc
            return None

    pathlib.Path.symlink_to = _safe_windows_symlink_to
    pathlib.WindowsPath.symlink_to = _safe_windows_symlink_to