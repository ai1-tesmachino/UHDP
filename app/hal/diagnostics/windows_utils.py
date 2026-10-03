import json
import subprocess
from typing import Any


def run_powershell(
    command: str,
) -> Any:

    result = subprocess.run(
        [
            "powershell",
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