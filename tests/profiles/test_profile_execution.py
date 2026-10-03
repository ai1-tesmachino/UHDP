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