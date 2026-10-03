from fastapi.testclient import (
    TestClient,
)

from app.main import app
from app.profiles.file_profile_repository import (
    FileProfileRepository,
)
from app.profiles.profile_service import (
    ProfileService,
)

client = TestClient(app)


def setup_module():

    service = ProfileService(
        FileProfileRepository(
            "profiles"
        )
    )

    service.install_builtin_profiles()


def test_list_profiles():

    response = client.get(
        "/profiles/"
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert len(data) >= 5


def test_get_profile():

    response = client.get(
        "/profiles/quick_test"
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data["name"]
        == "quick_test"
    )

    assert (
        "cpu"
        in data["diagnostics"]
    )