"""Stack Exchange — track de contribuciones.

Busca preguntas recientes **sin ninguna respuesta** en los tags de mis
verticales. Es la fuente con mejor relación esfuerzo/visibilidad: responder
bien una pregunta sin responder deja un artefacto permanente e indexado.

Cuota: 300 peticiones/día por IP sin key; 10.000/día registrando una app en
https://stackapps.com/apps/oauth/register (gratis, sin revisión). Sin key
esta fuente se agota en el primer ciclo — el adapter avisa.

Coste por ciclo = nº de sites × nº de tags (la API trata `tagged` como AND,
así que no se pueden agrupar tags en una sola llamada). Con 3 sites y 11
tags son 33 llamadas: a 15 min de intervalo, ~3.200/día. Cabe en 10.000.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from painradar.config import Profiles, Settings, get_profiles, get_settings
from painradar.logging_setup import get_logger
from painradar.models.enums import Track
from painradar.models.schemas import NormalizedOpportunity
from painradar.sources.base import HttpSourceAdapter

log = get_logger(__name__)

API_BASE = "https://api.stackexchange.com/2.3"
SEARCH_PATH = "/search/advanced"
_TAG_RE = re.compile(r"<[^>]+>")


class StackExchangeAdapter(HttpSourceAdapter):
    name = "stackexchange"
    track = Track.CONTRIB
    base_url = API_BASE

    def __init__(
        self,
        settings: Settings | None = None,
        profiles: Profiles | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.profiles = profiles or get_profiles()
        super().__init__(client=client)

    def is_configured(self) -> bool:
        # Técnicamente funciona sin key, pero 300 req/día no dan para operar.
        return bool(self.settings.stackexchange_key)

    async def fetch(self, limit: int = 50) -> list[NormalizedOpportunity]:
        cfg = self.profiles.contrib.stackexchange
        filtros = self.profiles.contrib.filtros
        since = datetime.now(tz=UTC) - timedelta(hours=filtros.max_antiguedad_horas)
        fromdate = int(since.timestamp())

        collected: dict[str, NormalizedOpportunity] = {}
        quota_remaining: int | None = None

        for site in cfg.sites:
            for tag in cfg.tags:
                if len(collected) >= limit:
                    break
                payload = await self._request_json(
                    SEARCH_PATH, params=self._params(site, tag, fromdate)
                )
                quota_remaining = payload.get("quota_remaining", quota_remaining)
                for raw in payload.get("items") or []:
                    normalized = self.normalize(raw, site)
                    if normalized is not None:
                        collected[normalized.external_id] = normalized

        log.info(
            "fuente.fetch",
            source=self.name,
            encontrados=len(collected),
            quota_remaining=quota_remaining,
        )
        return list(collected.values())[:limit]

    def _params(self, site: str, tag: str, fromdate: int) -> dict[str, Any]:
        params: dict[str, Any] = {
            "site": site,
            "tagged": tag,
            "fromdate": fromdate,
            "answers": 0,  # sin ninguna respuesta: ahí es donde aporto
            "accepted": "False",
            "order": "desc",
            "sort": "creation",
            "pagesize": 30,
            "filter": "withbody",  # sin esto no viene el cuerpo de la pregunta
        }
        if self.settings.stackexchange_key:
            params["key"] = self.settings.stackexchange_key
        return params

    # -------------------------------------------------------------- normalize

    def normalize(self, raw: dict[str, Any], site: str) -> NormalizedOpportunity | None:
        question_id = raw.get("question_id")
        link = raw.get("link")
        if question_id is None or not link:
            return None

        owner = raw.get("owner") or {}
        return NormalizedOpportunity(
            source_name=self.name,
            track=self.track,
            external_id=f"{site}:{question_id}",
            url=link,
            title=html.unescape(raw.get("title") or "(sin título)"),
            description=strip_html(raw.get("body") or "")[:8000],
            author=owner.get("display_name"),
            tags=list(raw.get("tags") or []),
            published_at=_epoch_to_dt(raw.get("creation_date")),
            container=site,
            engagement_count=raw.get("answer_count"),
            is_answered=bool(raw.get("is_answered")),
            score=raw.get("score"),
            raw=raw,
        )


def strip_html(value: str) -> str:
    """El cuerpo viene en HTML; para el clasificador basta el texto plano."""
    return html.unescape(_TAG_RE.sub(" ", value)).strip()


def _epoch_to_dt(value: Any) -> datetime:
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (TypeError, ValueError):
        return datetime.now(tz=UTC)
