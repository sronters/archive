from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from medarchive_application.catalog_import import (
    parse_partner_catalog_json,
    parse_service_catalog_json,
)
from medarchive_application.remote_catalog_sync import (
    RemotePartnerCatalogSnapshot,
    RemoteServiceCatalogSnapshot,
)


@dataclass(frozen=True)
class RemoteCatalogHttpConfig:
    service_catalog_url: str
    partner_catalog_url: str
    bearer_token: str | None = None
    timeout_seconds: float = 10.0


class HttpJsonRemoteCatalogClient:
    def __init__(self, config: RemoteCatalogHttpConfig) -> None:
        self._config = config

    def fetch_services(self, *, cursor: str | None) -> RemoteServiceCatalogSnapshot:
        payload, next_cursor = self._get_json(self._config.service_catalog_url, cursor=cursor)
        records, issues, _total = parse_service_catalog_json(json.dumps(payload).encode())
        if issues:
            codes = ", ".join(issue.code for issue in issues)
            raise ValueError(f"Remote service catalog payload failed validation: {codes}")
        return RemoteServiceCatalogSnapshot(
            records=records,
            cursor=next_cursor,
            fetched_at=datetime.now(timezone.utc),  # noqa: UP017
        )

    def fetch_partners(self, *, cursor: str | None) -> RemotePartnerCatalogSnapshot:
        payload, next_cursor = self._get_json(self._config.partner_catalog_url, cursor=cursor)
        records, issues, _total = parse_partner_catalog_json(json.dumps(payload).encode())
        if issues:
            codes = ", ".join(issue.code for issue in issues)
            raise ValueError(f"Remote partner catalog payload failed validation: {codes}")
        return RemotePartnerCatalogSnapshot(
            records=records,
            cursor=next_cursor,
            fetched_at=datetime.now(timezone.utc),  # noqa: UP017
        )

    def _get_json(self, url: str, *, cursor: str | None) -> tuple[object, str | None]:
        query = {"cursor": cursor} if cursor else {}
        request_url = f"{url}?{urlencode(query)}" if query else url
        headers = {"Accept": "application/json"}
        if self._config.bearer_token:
            headers["Authorization"] = f"Bearer {self._config.bearer_token}"
        request = Request(request_url, headers=headers, method="GET")
        with urlopen(request, timeout=self._config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, dict):
            return payload.get("items", payload), _optional_string(payload.get("next_cursor"))
        return payload, None


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
