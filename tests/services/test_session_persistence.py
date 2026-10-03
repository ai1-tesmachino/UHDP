from app.services.file_session_repository import (
    FileSessionRepository,
)


def test_repository_persists_session(
    tmp_path,
):

    repository = (
        FileSessionRepository(
            str(tmp_path)
        )
    )

    session = {
        "session_id": "abc123",
        "status": "completed",
    }

    repository.save(
        session
    )

    loaded = repository.get(
        "abc123"
    )

    assert loaded is not None
    assert (
        loaded["session_id"]
        == "abc123"
    )