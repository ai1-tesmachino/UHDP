from app.profiles.diagnostic_profile import DiagnosticProfile
from app.profiles.file_profile_repository import FileProfileRepository


def test_save_and_load_profile(tmp_path):
    repository = FileProfileRepository(tmp_path)

    profile = DiagnosticProfile(
        name="quick_test",
        diagnostics=["cpu", "memory"],
    )

    repository.save(profile)

    loaded = repository.get("quick_test")

    assert loaded is not None
    assert loaded.name == "quick_test"
    assert loaded.diagnostics == ["cpu", "memory"]


def test_list_profiles(tmp_path):
    repository = FileProfileRepository(tmp_path)

    repository.save(
        DiagnosticProfile(
            name="a",
            diagnostics=["cpu"],
        )
    )

    repository.save(
        DiagnosticProfile(
            name="b",
            diagnostics=["memory"],
        )
    )

    profiles = repository.list()

    assert len(profiles) == 2


def test_delete_profile(tmp_path):
    repository = FileProfileRepository(tmp_path)

    repository.save(
        DiagnosticProfile(
            name="quick_test",
            diagnostics=["cpu"],
        )
    )

    repository.delete("quick_test")

    assert repository.get("quick_test") is None