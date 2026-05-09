from __future__ import annotations

import os
from typing import Any, Mapping

import httpx


class AsyncHttpClient:
    def __init__(
        self,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        follow_redirects: bool = True,
    ):
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers=dict(headers or {}),
            follow_redirects=follow_redirects,
        )

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        response = await self._client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def get_json(self, url: str, **kwargs) -> Any:
        response = await self.get(url, **kwargs)
        return response.json()

    async def post_json(self, url: str, **kwargs) -> Any:
        response = await self.post(url, **kwargs)
        return response.json()

    async def close(self):
        await self._client.aclose()


class HttpUtils:
    @staticmethod
    def request(method: str, url: str, timeout: float = 30.0, **kwargs) -> httpx.Response:
        response = httpx.request(
            method,
            url,
            timeout=timeout,
            follow_redirects=True,
            **kwargs,
        )
        response.raise_for_status()
        return response

    @staticmethod
    def get(url: str, timeout: float = 30.0, **kwargs) -> httpx.Response:
        return HttpUtils.request("GET", url, timeout=timeout, **kwargs)

    @staticmethod
    def get_json(url: str, timeout: float = 30.0, **kwargs) -> Any:
        response = HttpUtils.get(url, timeout=timeout, **kwargs)
        return response.json()

    @staticmethod
    def download_file(url: str, file_path: str, timeout: float = 30.0, **kwargs) -> None:
        response = HttpUtils.get(url, timeout=timeout, **kwargs)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(response.content)
