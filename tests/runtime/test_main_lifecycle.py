from fastapi.testclient import TestClient

from app.main import app
from app.runtime.models.status import RuntimeStatus


def test_application_lifecycle():
    with TestClient(app):
        application = app.state.application

        assert application.status is RuntimeStatus.RUNNING
        assert app.state.runtime is application.runtime

    assert application.status is RuntimeStatus.STOPPED
