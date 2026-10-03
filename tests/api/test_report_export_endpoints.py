from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.reports import router


app = FastAPI()

app.include_router(
    router
)

client = TestClient(
    app
)


def test_missing_json_report():

    response = client.get(
        "/reports/missing/json"
    )

    assert (
        response.status_code
        == 404
    )


def test_missing_html_report():

    response = client.get(
        "/reports/missing/html"
    )

    assert (
        response.status_code
        == 404
    )