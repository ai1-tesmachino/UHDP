from app.profiles.file_profile_repository import (
    FileProfileRepository,
)
from app.profiles.profile_service import (
    ProfileService,
)


class FakeDiagnosticService:

    def execute(
        self,
        diagnostic_type,
        device_id,
        parameters=None,
    ):
        return {
            "diagnostic": diagnostic_type,
            "device_id": device_id,
        }


def test_execute_profile(tmp_path):

    repository = (
        FileProfileRepository(
            tmp_path
        )
    )

    service = ProfileService(
        repository
    )

    service.create_profile(
        name="quick_test",
        diagnostics=[
            "cpu",
            "memory",
        ],
    )

    results = (
        service.execute_profile(
            profile_name="quick_test",
            diagnostic_service=(
                FakeDiagnosticService()
            ),
            device_id="cpu",
        )
    )

    assert len(results) == 2

    assert results[0][
        "diagnostic"
    ] == "cpu"

    assert results[1][
        "diagnostic"
    ] == "memory"


def test_profile_selection_must_be_unique_and_belong_to_profile(tmp_path):
    service = ProfileService(FileProfileRepository(tmp_path))
    service.create_profile("cpu_only", ["cpu"])

    for selected in (["memory"], ["cpu", "cpu"]):
        try:
            service.execute_profile(
                profile_name="cpu_only",
                diagnostic_service=FakeDiagnosticService(),
                device_id="device-1",
                diagnostics=selected,
            )
        except ValueError as exc:
            assert "unique members" in str(exc)
        else:
            raise AssertionError("Invalid profile selection was accepted")