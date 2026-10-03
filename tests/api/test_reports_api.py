from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_reports_endpoint():

    response = client.get(
        "/reports/"
    )

    assert response.status_code == 200


def test_report_not_found():

    response = client.get(
        "/reports/does-not-exist"
    )

    assert response.status_code == 404