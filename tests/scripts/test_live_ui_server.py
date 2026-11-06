from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from http.server import ThreadingHTTPServer
from functools import partial

from scripts.serve_uhdp_ui import SpaRequestHandler, serve


@pytest.fixture
def ui_server(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        '<div id="root">UHDP</div>',
        encoding="utf-8",
    )
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("const ready = true;", encoding="utf-8")

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(SpaRequestHandler, directory=str(tmp_path)),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_live_ui_server_returns_spa_for_client_routes(ui_server: str):
    with urlopen(f"{ui_server}/execution?device=system", timeout=2) as response:
        assert response.status == 200
        assert b'<div id="root">UHDP</div>' in response.read()


def test_live_ui_server_serves_bundled_assets(ui_server: str):
    with urlopen(f"{ui_server}/assets/app.js", timeout=2) as response:
        assert response.status == 200
        assert response.read() == b"const ready = true;"


def test_live_ui_server_does_not_fallback_for_missing_assets(ui_server: str):
    with pytest.raises(HTTPError) as error:
        urlopen(f"{ui_server}/assets/missing.js", timeout=2)
    assert error.value.code == 404


def test_live_ui_server_reports_missing_production_build(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Built UHDP UI is missing"):
        serve(tmp_path)
