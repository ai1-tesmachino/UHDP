from app.services.file_session_repository import (
    FileSessionRepository,
)


def test_save_and_load_session(
    tmp_path,
):

    repository = (
        FileSessionRepository(
            str(tmp_path)
        )
    )

    session = {
        "session_id": "session-1",
        "status": "completed",
    }

    repository.save(
        session
    )

    loaded = repository.get(
        "session-1"
    )

    assert loaded is not None
    assert (
        loaded["session_id"]
        == "session-1"
    )


def test_list_sessions(
    tmp_path,
):

    repository = (
        FileSessionRepository(
            str(tmp_path)
        )
    )

    repository.save(
        {
            "session_id": "s1",
        }
    )

    repository.save(
        {
            "session_id": "s2",
        }
    )

    sessions = (
        repository.list_all()
    )

    assert len(sessions) == 2


def test_delete_session(
    tmp_path,
):

    repository = (
        FileSessionRepository(
            str(tmp_path)
        )
    )

    repository.save(
        {
            "session_id": "s1",
        }
    )

    repository.delete(
        "s1"
    )

    assert (
        repository.get("s1")
        is None
    )