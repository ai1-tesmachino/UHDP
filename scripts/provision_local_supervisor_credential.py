#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import secrets
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.local_reopen_auth import create_credential_hash


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Provision the local UHDP supervisor credential."
    )
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="Replace an existing credential after explicit confirmation.",
    )
    args = parser.parse_args(argv)

    if os.name != "posix":
        print(
            "Run this provisioning command on the Linux deployment host so "
            "credential-file permissions can be enforced.",
            file=sys.stderr,
        )
        return 1

    from app.core.config import get_settings

    credential_directory = Path(get_settings().DATA_DIR) / "local_auth"
    credential_path = credential_directory / "supervisor.credential"
    if credential_directory.is_symlink() or credential_path.is_symlink():
        print("Refusing to write through a symlinked credential path.", file=sys.stderr)
        return 1
    if credential_path.exists():
        if not args.rotate:
            print(
                f"A supervisor credential already exists at {credential_path}. "
                "Use --rotate to replace it.",
                file=sys.stderr,
            )
            return 1
        existing_stat = credential_path.stat()
        if (
            not stat.S_ISREG(existing_stat.st_mode)
            or existing_stat.st_uid != os.geteuid()
            or stat.S_IMODE(existing_stat.st_mode) != 0o600
        ):
            print(
                "The existing credential must be a regular file owned by the "
                "current operator with mode 0600 before rotation.",
                file=sys.stderr,
            )
            return 1
        if input(
            "Type ROTATE to replace the existing local supervisor credential: "
        ) != "ROTATE":
            print("Credential rotation cancelled.", file=sys.stderr)
            return 1
    elif args.rotate:
        print(
            f"No existing supervisor credential to rotate at {credential_path}.",
            file=sys.stderr,
        )
        return 1

    password = getpass.getpass("New local supervisor credential: ")
    confirmation = getpass.getpass("Confirm local supervisor credential: ")
    if password != confirmation:
        print("Credentials did not match.", file=sys.stderr)
        return 1

    try:
        encoded = create_credential_hash(password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    credential_directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(credential_directory, 0o700)
    directory_owner = credential_directory.stat().st_uid
    if directory_owner != os.geteuid():
        print(
            "The credential directory must be owned by the current operator.",
            file=sys.stderr,
        )
        return 1

    temporary_path = credential_directory / f".supervisor.{secrets.token_hex(8)}.tmp"
    descriptor = os.open(
        temporary_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(f"{encoded}\n")
            file.flush()
            os.fsync(file.fileno())
        os.chmod(temporary_path, 0o600)
        if args.rotate:
            os.replace(temporary_path, credential_path)
        else:
            try:
                os.link(temporary_path, credential_path)
            except FileExistsError:
                temporary_path.unlink()
                print(
                    f"A supervisor credential already exists at {credential_path}; "
                    "refusing to overwrite it.",
                    file=sys.stderr,
                )
                return 1
            temporary_path.unlink()
        directory_descriptor = os.open(credential_directory, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise

    if stat.S_IMODE(credential_directory.stat().st_mode) != 0o700:
        print("Could not enforce credential directory mode 0700.", file=sys.stderr)
        return 1
    if stat.S_IMODE(credential_path.stat().st_mode) != 0o600:
        print("Could not enforce credential file mode 0600.", file=sys.stderr)
        return 1
    action = "Updated" if args.rotate else "Created"
    print(f"{action} {credential_path} with a salted PBKDF2 hash (mode 0600).")
    print("Restart the UHDP backend for the new credential to take effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
