from __future__ import annotations

import httpx


class Client:
    def __init__(self, base: str, token: str) -> None:
        self.base = base.rstrip("/")
        self.token = token
        self._http = httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def pair(self, code: str) -> dict:
        r = self._http.post(f"{self.base}/v1/connections/pair", json={"code": code})
        r.raise_for_status()
        data = r.json()
        self.token = data["token"]
        return data

    def search(self, query: str, purpose: str, project: str | None = None) -> dict:
        return self.call(
            "search_personal_context",
            query=query,
            purpose=purpose,
            scope={"project": project} if project else {},
        )

    def call(self, tool: str, **kwargs) -> dict:
        r = self._http.post(
            f"{self.base}/v1/mcp/tools/{tool}", headers=self._headers(), json=kwargs
        )
        r.raise_for_status()
        return r.json()

    def resource(self, uri: str) -> dict:
        r = self._http.get(
            f"{self.base}/v1/mcp/resources", headers=self._headers(), params={"uri": uri}
        )
        r.raise_for_status()
        return r.json()
