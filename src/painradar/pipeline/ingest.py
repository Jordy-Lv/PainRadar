"""Ingesta: fetch -> normalizar -> deduplicar -> guardar.

Es el único camino por el que entra algo a la base. En modo `discovery` esto
es todo lo que corre: captura sin filtrar y sin llamar a la IA, para que la
fase 0 mida la demanda real en vez de adivinarla.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from painradar.logging_setup import get_logger
from painradar.models import Opportunity, Outcome, Source
from painradar.models.enums import OutcomeStatus
from painradar.models.schemas import NormalizedOpportunity
from painradar.pipeline.dedupe import filter_new
from painradar.sources import DEFAULT_POLL_INTERVALS, HttpSourceAdapter
from painradar.sources.base import SourceError, SourceNotConfigured

log = get_logger(__name__)


@dataclass
class IngestResult:
    source: str
    fetched: int = 0
    new: int = 0
    duplicates: int = 0
    error: str | None = None
    items: list[NormalizedOpportunity] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None


def get_or_create_source(session: Session, adapter: HttpSourceAdapter) -> Source:
    source = session.execute(select(Source).where(Source.name == adapter.name)).scalar_one_or_none()
    if source is None:
        source = Source(
            name=adapter.name,
            track=adapter.track,
            enabled=True,
            poll_interval_seconds=DEFAULT_POLL_INTERVALS.get(adapter.name, 300),
            config_json={},
        )
        session.add(source)
        session.flush()
        log.info("fuente.registrada", source=adapter.name, track=str(adapter.track))
    return source


def persist(
    session: Session, source: Source, items: list[NormalizedOpportunity]
) -> list[Opportunity]:
    """Guarda oportunidades nuevas, cada una con su fila de outcome en `new`."""
    now = datetime.now(tz=UTC)
    created: list[Opportunity] = []

    for item in items:
        opportunity = Opportunity(
            source_id=source.id,
            track=item.track,
            external_id=item.external_id,
            url=str(item.url),
            title=item.title,
            description=item.description,
            author=item.author,
            tags_json=item.tags,
            published_at=item.published_at,
            fetched_at=now,
            budget_min=item.budget_min,
            budget_max=item.budget_max,
            currency=item.currency,
            is_hourly=item.is_hourly,
            bids_count=item.bids_count,
            client_country=item.client_country,
            client_rating=item.client_rating,
            client_spend=item.client_spend,
            client_payment_verified=item.client_payment_verified,
            container=item.container,
            engagement_count=item.engagement_count,
            is_answered=item.is_answered,
            score=item.score,
            raw_json=item.raw,
        )
        # Sin outcome no hay reporte semanal ni forma de ajustar el filtro.
        opportunity.outcome = Outcome(status=OutcomeStatus.NEW, updated_at=now)
        session.add(opportunity)
        created.append(opportunity)

    session.flush()
    return created


async def ingest_source(
    session: Session,
    adapter: HttpSourceAdapter,
    limit: int = 50,
    *,
    dry_run: bool = False,
) -> IngestResult:
    """Un ciclo completo de una fuente. Nunca lanza: devuelve el error dentro."""
    result = IngestResult(source=adapter.name)

    try:
        items = await adapter.fetch(limit=limit)
    except SourceNotConfigured as exc:
        result.error = f"no configurada: {exc}"
        log.info("ingesta.omitida", source=adapter.name, motivo=str(exc))
        return result
    except SourceError as exc:
        result.error = str(exc)
        log.error("ingesta.fallo", source=adapter.name, error=str(exc))
        return result

    result.fetched = len(items)

    if dry_run:
        result.items = items
        result.new = len(items)
        return result

    source = get_or_create_source(session, adapter)
    source.last_fetch_at = datetime.now(tz=UTC)

    fresh = filter_new(session, items, {adapter.name: source.id})
    result.new = len(fresh)
    result.duplicates = result.fetched - result.new
    result.items = fresh

    persist(session, source, fresh)
    source.last_success_at = datetime.now(tz=UTC)

    log.info(
        "ingesta.ok",
        source=adapter.name,
        traidos=result.fetched,
        nuevos=result.new,
        duplicados=result.duplicates,
    )
    return result
