
from app.profiles.diagnostic_profile import DiagnosticProfile
from app.profiles.profile_repository import ProfileRepository


class ProfileService:

    def __init__(self, repository: ProfileRepository):
        self.repository = repository

    def create_profile(
        self,
        name: str,
        diagnostics: list[str],
        description: str = "",
    ) -> DiagnosticProfile:
        profile = DiagnosticProfile(
            name=name,
            diagnostics=diagnostics,
            description=description,
        )

        self.repository.save(profile)

        return profile

    def get_profile(self, name: str) -> DiagnosticProfile | None:
        return self.repository.get(name)

    def list_profiles(self) -> list[DiagnosticProfile]:
        return self.repository.list()

    def delete_profile(self, name: str) -> None:
        self.repository.delete(name)

    def install_builtin_profiles(self) -> None:
        builtins = [
            DiagnosticProfile(
                name="quick_test",
                diagnostics=[
                    "cpu",
                    "memory",
                ],
                description="Quick hardware validation",
            ),
            DiagnosticProfile(
                name="extended_test",
                diagnostics=[
                    "cpu",
                    "memory",
                    "storage",
                    "network",
                ],
                description="Extended diagnostic suite",
            ),
            DiagnosticProfile(
                name="manufacturing_qa",
                diagnostics=[
                    "cpu",
                    "memory",
                    "storage",
                    "network",
                ],
                description="Manufacturing QA profile",
            ),
            DiagnosticProfile(
                name="refurbishment_qa",
                diagnostics=[
                    "cpu",
                    "memory",
                    "storage",
                    "network",
                ],
                description="Refurbishment validation profile",
            ),
            DiagnosticProfile(
                name="service_center_qa",
                diagnostics=[
                    "cpu",
                    "memory",
                    "storage",
                    "network",
                ],
                description="Service center diagnostic profile",
            ),
        ]

        for profile in builtins:
            self.repository.save(profile)

    def execute_profile(
        self,
        profile_name: str,
        diagnostic_service,
        device_id: str,
    ):
        profile = self.get_profile(
            profile_name
        )

        if profile is None:
            raise ValueError(
                f"Profile not found: {profile_name}"
            )

        results = []

        for diagnostic in (
            profile.diagnostics
        ):
            result = (
                diagnostic_service.execute(
                    diagnostic_type=diagnostic,
                    device_id=device_id,
                )
            )

            results.append(
                result
            )

        return results