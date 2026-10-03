from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.reports_export import router


app = FastAPI()

app.include_router(
    router
)

client = TestClient(
    app
)


def test_report_not_found():

    response = client.get(
        "/reports/export/missing"
    )

    assert response.status_code == 404


def test_json_report_not_found():

    response = client.get(
        "/reports/export/missing/json"
    )

    assert response.status_code == 404


def test_html_report_not_found():

    response = client.get(
        "/reports/export/missing/html"
    )

    assert response.status_code == 404