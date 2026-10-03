import json
from pathlib import Path

from app.profiles.diagnostic_profile import DiagnosticProfile
from app.profiles.profile_repository import ProfileRepository


class FileProfileRepository(ProfileRepository):

    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, profile: DiagnosticProfile) -> None:
        path = self.storage_path / f"{profile.name}.json"

        with open(path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "name": profile.name,
                    "description": profile.description,
                    "diagnostics": profile.diagnostics,
                },
                file,
                indent=2,
            )

    def get(self, name: str) -> DiagnosticProfile | None:
        path = self.storage_path / f"{name}.json"

        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return DiagnosticProfile(
            name=data["name"],
            description=data.get("description", ""),
            diagnostics=data.get("diagnostics", []),
        )

    def list(self) -> list[DiagnosticProfile]:
        profiles = []

        for file_path in self.storage_path.glob("*.json"):
            profile = self.get(file_path.stem)

            if profile:
                profiles.append(profile)

        profiles.sort(key=lambda p: p.name)

        return profiles

    def delete(self, name: str) -> None:
        path = self.storage_path / f"{name}.json"

        if path.exists():
            path.unlink()