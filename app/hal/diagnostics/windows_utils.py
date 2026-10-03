import json
import shutil
import subprocess
from typing import Any


class PowerShellUnavailableError(RuntimeError):
    pass


def run_powershell(
    command: str,
) -> Any:
    executable = shutil.which("powershell")
    if executable is None:
        raise PowerShellUnavailableError(
            "Windows PowerShell is unavailable on this system"
        )

    result = subprocess.run(
        [
            executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or "PowerShell command failed"
        )

    output = result.stdout.strip()

    if not output:
        return []

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return output


def as_list(
    value: Any,
) -> list:

    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]