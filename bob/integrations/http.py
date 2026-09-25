from __future__ import annotations

from typing import Any

import requests

from bob.errors import ExternalEffectError


class JsonHttp:
    def __init__(self, base_url: str, headers: dict[str, str] | None = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        data: Any = None,
    ) -> Any:
        url = self.base_url + (path if path.startswith("/") else "/" + path)
        response = requests.request(
            method,
            url,
            headers=self.headers,
            params=params,
            json=json_body,
            data=data,
            timeout=self.timeout,
        )
        if not response.ok:
            snippet = response.text[:1000]
            raise ExternalEffectError(
                f"{method} {url} failed ({response.status_code}): {snippet}",
                status_code=response.status_code,
            )
        if not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.json()
        return response.text
