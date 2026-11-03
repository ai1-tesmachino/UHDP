from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import secrets
import uuid

from cloud.auth import password_hash
from cloud.config import CloudSettings
from cloud.database import CloudDatabase


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Controlled cloud onboarding; there is no public registration API."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    company = commands.add_parser("create-company")
    company.add_argument("--company-id", default=str(uuid.uuid4()))
    company.add_argument("--name", required=True)
    station = commands.add_parser("create-station")
    station.add_argument("--company-id", required=True)
    station.add_argument("--station-id", default=str(uuid.uuid4()))
    station.add_argument("--name", required=True)
    user = commands.add_parser("create-user")
    user.add_argument("--company-id", required=True)
    user.add_argument("--username", required=True)
    user.add_argument(
        "--role",
        required=True,
        choices=("administrator", "supervisor", "technician", "analyst"),
    )
    args = parser.parse_args()
    database = CloudDatabase(CloudSettings.from_env())
    database.migrate()

    with database.connection() as connection:
        if args.command == "create-company":
            connection.execute(
                "INSERT INTO companies (company_id, name) VALUES (%s, %s)",
                (args.company_id, args.name),
            )
            print(f"Company created: {args.company_id}")
        elif args.command == "create-station":
            token = secrets.token_urlsafe(48)
            connection.execute(
                """
                INSERT INTO stations (
                    station_id, company_id, name, token_sha256, status
                ) VALUES (%s, %s, %s, %s, 'active')
                """,
                (
                    args.station_id,
                    args.company_id,
                    args.name,
                    hashlib.sha256(token.encode()).hexdigest(),
                ),
            )
            print(f"Station created: {args.station_id}")
            print("Copy this station token to a protected local environment file now:")
            print(token)
            print("It cannot be retrieved from the cloud database.")
        elif args.command == "create-user":
            password = getpass.getpass("Initial password (12+ characters): ")
            confirmation = getpass.getpass("Confirm password: ")
            if not secrets.compare_digest(password, confirmation):
                raise SystemExit("Passwords did not match.")
            encoded = password_hash(password)
            user_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO users (
                    user_id, company_id, username, password_hash, role_id
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, args.company_id, args.username, encoded, args.role),
            )
            print(f"User created: {user_id}")


if __name__ == "__main__":
    main()
