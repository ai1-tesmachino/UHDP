import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings


class SupabaseRestStore:
    """Small synchronous PostgREST client using a server-only service key."""

    def __init__(
        self,
        url: str,
        service_role_key: str,
        table: str = "uhdp_records",
    ) -> None:
        self._url = url.rstrip("/")
        self._service_role_key = service_role_key
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise ValueError("SUPABASE_RECORDS_TABLE must be a simple table name.")
        self._table = table

    @classmethod
    def from_settings(cls) -> "SupabaseRestStore":
        settings = get_settings()
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "STORAGE_BACKEND=supabase requires SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY to be configured on the backend."
            )
        return cls(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
            settings.SUPABASE_RECORDS_TABLE,
        )

    def upsert(self, record_type: str, record_id: str, payload: Any) -> None:
        self._request(
            "POST",
            query={"on_conflict": "record_type,id"},
            body=[{
                "record_type": record_type,
                "id": record_id,
                "payload": payload,
            }],
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def get(self, record_type: str, record_id: str) -> Any | None:
        rows = self._request(
            "GET",
            query={
                "record_type": f"eq.{record_type}",
                "id": f"eq.{record_id}",
                "select": "payload",
                "limit": "1",
            },
        )
        return rows[0]["payload"] if rows else None

    def list(self, record_type: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            query={
                "record_type": f"eq.{record_type}",
                "select": "id,payload,updated_at",
                "order": "updated_at.desc",
            },
        )
        if not isinstance(rows, list):
            raise RuntimeError("Supabase returned an invalid record list.")
        return rows

    def delete(self, record_type: str, record_id: str) -> None:
        self._request(
            "DELETE",
            query={
                "record_type": f"eq.{record_type}",
                "id": f"eq.{record_id}",
            },
            prefer="return=minimal",
        )

    def _request(
        self,
        method: str,
        query: dict[str, str],
        body: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
        query_string = urlencode(query)
        endpoint = f"{self._url}/rest/v1/{self._table}?{query_string}"
        headers = {
            "apikey": self._service_role_key,
            "Authorization": f"Bearer {self._service_role_key}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer
        request = Request(
            endpoint,
            data=json.dumps(body, default=str).encode("utf-8") if body is not None else None,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=20) as response:
                response_body = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Supabase request failed with HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise RuntimeError(
                f"Could not connect to Supabase: {error.reason}"
            ) from error
        except TimeoutError as error:
            raise RuntimeError("Supabase request timed out.") from error

        if not response_body:
            return None
        try:
            return json.loads(response_body)
        except json.JSONDecodeError as error:
            raise RuntimeError("Supabase returned invalid JSON.") from error
