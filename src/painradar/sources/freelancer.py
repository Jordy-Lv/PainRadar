"""Freelancer.com — fuente principal del track de ventas.

Usa la API REST oficial (`projects/0.1/projects/active`) con el header
`Freelancer-OAuth-V1`. No se usa el SDK oficial de Python: sigue declarando
soporte de Python 2.7 y arrastra dependencias muertas.

Los nombres de campo siguen la documentación pública de la API. La
normalización es deliberadamente defensiva (`.get` en todo): un campo que
desaparezca no debe tumbar el ciclo entero, solo dejar ese dato en None.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from painradar.config import Settings, get_settings
from painradar.logging_setup import get_logger
from painradar.models.enums import Track
from painradar.models.schemas import NormalizedOpportunity
from painradar.sources.base import HttpSourceAdapter, SourceNotConfigured

log = get_logger(__name__)

PROJECTS_PATH = "/projects/0.1/projects/active/"
PAGE_SIZE = 50


class FreelancerAdapter(HttpSourceAdapter):
    name = "freelancer"
    track = Track.SALES

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.freelancer_base_url
        super().__init__(client=client)

    def is_configured(self) -> bool:
        return bool(self.settings.freelancer_oauth_token)

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        token = self.settings.freelancer_oauth_token
        if token:
            headers["Freelancer-OAuth-V1"] = token
        return headers

    async def fetch(self, limit: int = PAGE_SIZE) -> list[NormalizedOpportunity]:
        """Trae los proyectos activos más recientes, paginando por offset."""
        if not self.is_configured():
            raise SourceNotConfigured(
                "Falta FREELANCER_OAUTH_TOKEN "
                "(se genera en https://accounts.freelancer.com/settings/develop)"
            )

        collected: list[NormalizedOpportunity] = []
        offset = 0

        while len(collected) < limit:
            page_size = min(PAGE_SIZE, limit - len(collected))
            payload = await self._request_json(
                PROJECTS_PATH, params=self._params(limit=page_size, offset=offset)
            )
            projects, users = _unpack(payload)
            if not projects:
                break

            for raw in projects:
                normalized = self.normalize(raw, users)
                if normalized is not None:
                    collected.append(normalized)

            if len(projects) < page_size:
                break  # última página
            offset += page_size

        log.info("fuente.fetch", source=self.name, encontrados=len(collected))
        return collected

    def _params(self, limit: int, offset: int) -> dict[str, Any]:
        return {
            "limit": limit,
            "offset": offset,
            # Sin esto la respuesta viene sin descripción ni datos del cliente,
            # que es justo lo que el clasificador necesita para decidir.
            "full_description": "true",
            "job_details": "true",
            "user_details": "true",
            "user_country_details": "true",
            "user_status": "true",
            "user_employer_reputation": "true",
            "sort_field": "time_updated",
            "project_statuses[]": "active",
        }

    # -------------------------------------------------------------- normalize

    def normalize(
        self, raw: dict[str, Any], users: dict[str, Any] | None = None
    ) -> NormalizedOpportunity | None:
        """Traduce un proyecto de Freelancer al vocabulario común."""
        project_id = raw.get("id")
        seo_url = raw.get("seo_url")
        if project_id is None or not seo_url:
            log.warning("freelancer.proyecto_incompleto", raw_id=project_id)
            return None

        budget = raw.get("budget") or {}
        currency = raw.get("currency") or {}
        bid_stats = raw.get("bid_stats") or {}
        owner = _owner_of(raw, users)

        published_epoch = raw.get("time_submitted") or raw.get("submitdate")

        return NormalizedOpportunity(
            source_name=self.name,
            track=self.track,
            external_id=str(project_id),
            url=f"https://www.freelancer.com/projects/{seo_url}",
            title=raw.get("title") or "(sin título)",
            description=raw.get("description") or raw.get("preview_description") or "",
            author=(owner.get("username") or owner.get("display_name")) if owner else None,
            tags=[job["name"] for job in raw.get("jobs") or [] if job.get("name")],
            published_at=_epoch_to_dt(published_epoch),
            budget_min=_as_float(budget.get("minimum")),
            budget_max=_as_float(budget.get("maximum")),
            currency=currency.get("code"),
            is_hourly=(raw.get("type") == "hourly"),
            bids_count=_as_int(bid_stats.get("bid_count")),
            client_country=_country_of(owner),
            client_rating=_rating_of(owner),
            client_payment_verified=_payment_verified_of(owner),
            raw=raw,
        )


# ------------------------------------------------------------------ helpers


def _unpack(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """La API envuelve todo en {"status": ..., "result": {...}}."""
    result = payload.get("result") or {}
    projects: list[dict[str, Any]] = result.get("projects") or []
    users: dict[str, Any] = result.get("users") or {}
    return projects, users


def _owner_of(raw: dict[str, Any], users: dict[str, Any] | None) -> dict[str, Any] | None:
    if not users:
        return None
    owner_id = raw.get("owner_id")
    if owner_id is None:
        return None
    # La API indexa `users` por id en forma de string.
    owner = users.get(str(owner_id))
    return owner if isinstance(owner, dict) else None


def _country_of(owner: dict[str, Any] | None) -> str | None:
    if not owner:
        return None
    country = owner.get("location", {}).get("country") or owner.get("country") or {}
    name = country.get("name") if isinstance(country, dict) else None
    return str(name) if name else None


def _rating_of(owner: dict[str, Any] | None) -> float | None:
    if not owner:
        return None
    reputation = owner.get("employer_reputation") or {}
    history = reputation.get("entire_history") or {}
    return _as_float(history.get("overall"))


def _payment_verified_of(owner: dict[str, Any] | None) -> bool | None:
    if not owner:
        return None
    status = owner.get("status") or {}
    value = status.get("payment_verified")
    return bool(value) if value is not None else None


def _epoch_to_dt(value: Any) -> datetime:
    """Freelancer manda timestamps Unix en segundos."""
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (TypeError, ValueError):
        return datetime.now(tz=UTC)


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
