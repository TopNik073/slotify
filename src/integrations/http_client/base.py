from typing import Any
from typing import Literal

import httpx

from src.core.logger import get_logger
from src.integrations.http_client.errors import HTTPClientError
from src.integrations.http_client.errors import HTTPClientTimeout

logger = get_logger(__name__)

Method = Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

_NO_CONTENT = 204


class BaseHTTPClient:
    """
    Thin async wrapper over httpx for talking to third-party APIs.

    A client is opened per request rather than kept alive: these services are instantiated per
    HTTP request by the dependency injection container, so a long-lived connection pool would
    live no longer than the request anyway and would need explicit shutdown handling.
    """

    def __init__(
        self,
        base_url: str = '',
        *,
        timeout: float = 10.0,
        default_headers: dict[str, str] | None = None,
    ):
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._default_headers = default_headers or {}

    def _url(self, path: str) -> str:
        if path.startswith(('http://', 'https://')):
            return path

        return f'{self._base_url}/{path.lstrip("/")}'

    async def request(  # noqa: PLR0913
        self,
        method: Method,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self._url(path)
        merged_headers = {**self._default_headers, **(headers or {})}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=merged_headers,
                )
        except httpx.TimeoutException as exc:
            await logger.aerror('HTTP request timed out', method=method, url=url)
            raise HTTPClientTimeout from exc
        except httpx.HTTPError as exc:
            await logger.aerror('HTTP request failed', method=method, url=url, error=str(exc))
            raise HTTPClientError from exc

        if response.is_error:
            await logger.aerror(
                'HTTP request returned an error',
                method=method,
                url=url,
                status=response.status_code,
                body=response.text[:2000],
            )
            raise HTTPClientError(
                message=f'{method} {url} returned {response.status_code}',
                status_code=response.status_code,
                payload=response.text,
            )

        if response.status_code == _NO_CONTENT or not response.content:
            return {}

        parsed = response.json()
        if not isinstance(parsed, dict):
            return {'data': parsed}

        return parsed
