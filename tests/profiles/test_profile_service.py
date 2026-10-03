from app.profiles.file_profile_repository import FileProfileRepository
from app.profiles.profile_service import ProfileService


def test_install_builtin_profiles(tmp_path):
    repository = FileProfileRepository(tmp_path)

    service = ProfileService(repository)

    service.install_builtin_profiles()

    profiles = service.list_profiles()

    assert len(profiles) == 5


def test_get_builtin_profile(tmp_path):
    repository = FileProfileRepository(tmp_path)

    service = ProfileService(repository)

    service.install_builtin_profiles()

    profile = service.get_profile("quick_test")

    assert profile is not None
    assert "cpu" in profile.diagnostics