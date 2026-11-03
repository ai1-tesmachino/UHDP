#!/usr/bin/env python3
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


UI_DIRECTORY = Path(__file__).resolve().parents[1] / "frontend" / "dist"


class SpaRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        request_path = unquote(urlsplit(self.path).path)
        requested_file = Path(self.translate_path(request_path))
        if not requested_file.exists() and not Path(request_path).suffix:
            original_path = self.path
            self.path = "/"
            try:
                super().do_GET()
            finally:
                self.path = original_path
            return
        super().do_GET()


def serve(directory: Path = UI_DIRECTORY, port: int = 3000) -> None:
    if not (directory / "index.html").is_file():
        raise FileNotFoundError(f"Built UHDP UI is missing: {directory / 'index.html'}")
    handler = partial(SpaRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
