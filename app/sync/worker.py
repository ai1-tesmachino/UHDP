from __future__ import annotations

import json
import logging
import http.client
import ssl
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.core.config import Settings, get_settings
from app.evidence.storage import EvidenceStorage
from app.persistence.local.database import SQLiteDatabase


logger = logging.getLogger(__name__)


class SyncWorker:
    def __init__(
        self,
        database: SQLiteDatabase,
        settings: Settings | None = None,
    ) -> None:
        self._database = database
        self._settings = settings or get_settings()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._database.recover_interrupted_sync()
        if not self._settings.CLOUD_API_URL or not self._settings.CLOUD_STATION_TOKEN:
            logger.info("Cloud sync is not configured; local outbox remains pending.")
            return
        parsed_endpoint = urlsplit(self._settings.CLOUD_API_URL)
        if parsed_endpoint.scheme != "https" and parsed_endpoint.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise RuntimeError(
                "Cloud synchronization requires HTTPS outside loopback development."
            )
        self._thread = threading.Thread(
            target=self._run,
            name="uhdp-cloud-sync",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(
                timeout=max(5, self._settings.SYNC_REQUEST_TIMEOUT_SECONDS + 2)
            )
            if self._thread.is_alive():
                logger.error("Cloud sync worker did not stop before shutdown timeout.")

    def _run(self) -> None:
        interval = max(2, self._settings.SYNC_INTERVAL_SECONDS)
        while not self._stop.is_set():
            events = self._database.claim_outbox()
            if events:
                self._send_batch(events)
                continue
            self._stop.wait(interval)

    def _send_batch(self, events: list[dict]) -> None:
        endpoint = f"{self._settings.CLOUD_API_URL.rstrip('/')}/v1/sync/events"
        request = Request(
            endpoint,
            data=json.dumps(
                {
                    "events": [
                        {
                            key: event[key]
                            for key in (
                                "event_id",
                                "event_type",
                                "entity_type",
                                "entity_id",
                                "schema_version",
                                "created_at",
                                "payload",
                                "boot_session_id",
                            )
                        }
                        for event in events
                    ]
                },
                separators=(",", ":"),
            ).encode(),
            headers={
                "Authorization": f"Bearer {self._settings.CLOUD_STATION_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(
                request,
                timeout=max(1, self._settings.SYNC_REQUEST_TIMEOUT_SECONDS),
            ) as response:
                payload = json.loads(response.read())
            accepted = set(payload.get("accepted_event_ids", []))
            rejected = payload.get("rejected", {})
            if not isinstance(rejected, dict):
                raise ValueError("Cloud returned an invalid rejection list.")
            for event in events:
                event_id = event["event_id"]
                if event_id in accepted:
                    try:
                        if event["entity_type"] == "evidence":
                            self._upload_evidence(event)
                    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                        self._database.fail_sync(event_id, str(exc))
                        continue
                    self._database.acknowledge_sync(event_id)
                elif event_id in rejected:
                    self._database.fail_sync(
                        event_id,
                        str(rejected[event_id]),
                    )
                else:
                    self._database.fail_sync(
                        event_id,
                        "Cloud response omitted an acknowledgement for this event.",
                    )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            logger.warning("Cloud event batch upload failed: %s", exc)
            for event in events:
                self._database.fail_sync(event["event_id"], str(exc))
        except Exception:
            logger.exception("Unexpected error while processing the sync batch.")
            for event in events:
                self._database.fail_sync(
                    event["event_id"],
                    "Unexpected sync worker error; see local application logs.",
                )

    def _upload_evidence(self, event: dict) -> None:
        evidence_id = event["entity_id"]
        storage = EvidenceStorage(database=self._database)
        metadata, stream = storage.open(evidence_id)
        with stream:
            upload = self._request_json(
                f"/v1/evidence/{evidence_id}/upload-url",
                {"sha256": metadata["sha256"]},
            )
            self._put_file(
                upload["upload_url"],
                stream,
                int(metadata["size_bytes"]),
                upload["headers"],
            )
        self._request_json(
            f"/v1/evidence/{evidence_id}/complete",
            {"sha256": metadata["sha256"]},
        )

    def _request_json(self, path: str, payload: dict) -> dict:
        endpoint = f"{self._settings.CLOUD_API_URL.rstrip('/')}{path}"
        request = Request(
            endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode(),
            headers={
                "Authorization": f"Bearer {self._settings.CLOUD_STATION_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(
            request,
            timeout=max(1, self._settings.SYNC_REQUEST_TIMEOUT_SECONDS),
        ) as response:
            result = json.loads(response.read())
        if not isinstance(result, dict):
            raise ValueError("Cloud returned an invalid evidence response.")
        return result

    def _put_file(
        self,
        url: str,
        stream,
        size_bytes: int,
        headers: dict[str, str],
    ) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Evidence upload destinations must use HTTPS.")
        connection = http.client.HTTPSConnection(
            parsed.hostname,
            parsed.port or 443,
            timeout=max(1, self._settings.SYNC_REQUEST_TIMEOUT_SECONDS),
            context=ssl.create_default_context(),
        )
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        try:
            connection.putrequest("PUT", path)
            for name, value in headers.items():
                connection.putheader(name, value)
            connection.putheader("Content-Length", str(size_bytes))
            connection.endheaders()
            sent = 0
            while chunk := stream.read(1024 * 1024):
                connection.send(chunk)
                sent += len(chunk)
            if sent != size_bytes:
                raise ValueError("Evidence size changed during upload.")
            response = connection.getresponse()
            response.read()
            if not 200 <= response.status < 300:
                raise OSError(
                    f"Object storage upload failed with HTTP {response.status}."
                )
        finally:
            connection.close()
