"""Contrato de las fuentes.

Todo adapter cumple `SourceAdapter`. Mientras lo cumpla, el resto del
pipeline no sabe ni le importa de dónde vino la oportunidad: cambiar una API
o añadir un foro nuevo no toca nada aguas abajo.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Protocol, runtime_checkable

import httpx

from painradar.logging_setup import get_logger
from painradar.models.enums import Track
from painradar.models.schemas import NormalizedOpportunity

log = get_logger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class SourceError(RuntimeError):
    """Fallo recuperable de una fuente: se registra y el ciclo continúa."""


class SourceNotConfigured(SourceError):
    """Falta un token o una credencial. No es un bug: es una fase no activada."""


@runtime_checkable
class SourceAdapter(Protocol):
    name: str
    track: Track

    def is_configured(self) -> bool:
        """False si falta credencial; el scheduler la salta sin ruido."""
        ...

    async def fetch(self, limit: int = 50) -> list[NormalizedOpportunity]:
        """Trae lo más reciente, ya normalizado. No escribe en la base."""
        ...


class HttpSourceAdapter:
    """Base con reintentos y backoff exponencial para fuentes sobre HTTP.

    El backoff respeta `Retry-After` cuando la API lo manda: pelearse con el
    rate limit de una API oficial es la forma más rápida de perder el acceso.
    """

    name: str = "http"
    track: Track = Track.SALES
    base_url: str = ""
    max_retries: int = 4

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    def is_configured(self) -> bool:
        """Cada subclase decide qué credenciales necesita."""
        return True

    async def fetch(self, limit: int = 50) -> list[NormalizedOpportunity]:
        """Implementado por cada fuente concreta."""
        raise NotImplementedError(f"{type(self).__name__} no implementa fetch()")

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "painradar/0.1"}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, timeout=DEFAULT_TIMEOUT, headers=self._headers()
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> HttpSourceAdapter:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request_json(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.get(path, params=params)
            except httpx.HTTPError as exc:
                last_error = exc
                await self._sleep_backoff(attempt)
                continue

            if response.status_code in RETRYABLE_STATUS:
                retry_after = _parse_retry_after(response)
                log.warning(
                    "fuente.rate_limit",
                    source=self.name,
                    status=response.status_code,
                    attempt=attempt + 1,
                    retry_after=retry_after,
                )
                await self._sleep_backoff(attempt, retry_after)
                last_error = SourceError(f"{self.name}: HTTP {response.status_code}")
                continue

            if response.status_code >= 400:
                raise SourceError(
                    f"{self.name}: HTTP {response.status_code} en {path} — {response.text[:200]}"
                )

            data: dict[str, Any] = response.json()
            return data

        raise SourceError(f"{self.name}: agotados {self.max_retries} intentos") from last_error

    async def _sleep_backoff(self, attempt: int, retry_after: float | None = None) -> None:
        if retry_after is not None:
            delay = retry_after
        else:
            # Exponencial con jitter: evita que varias fuentes reintenten a la vez.
            delay = min(2**attempt, 30) + random.uniform(0, 1)
        await asyncio.sleep(delay)


def _parse_retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
