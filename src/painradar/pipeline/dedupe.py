"""Deduplicación.

Dos claves, porque ninguna basta sola: `(source, external_id)` es la
identidad real dentro de una plataforma, y `url` atrapa el caso de una misma
oportunidad que llega por dos caminos (p. ej. Workana por IMAP y, más
adelante, por lectura directa).
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from painradar.models import Opportunity
from painradar.models.schemas import NormalizedOpportunity


def existing_keys(
    session: Session, items: Iterable[NormalizedOpportunity]
) -> tuple[set[str], set[tuple[str, str]]]:
    """Consulta en bloque qué urls y pares (fuente, id) ya están guardados."""
    items = list(items)
    if not items:
        return set(), set()

    urls = {str(item.url) for item in items}
    external_ids = {item.external_id for item in items}

    rows = session.execute(
        select(Opportunity.url, Opportunity.external_id, Opportunity.source_id).where(
            Opportunity.url.in_(urls) | Opportunity.external_id.in_(external_ids)
        )
    ).all()

    known_urls = {row.url for row in rows}
    known_pairs = {(str(row.source_id), row.external_id) for row in rows}
    return known_urls, known_pairs


def filter_new(
    session: Session,
    items: Iterable[NormalizedOpportunity],
    source_ids: dict[str, int],
) -> list[NormalizedOpportunity]:
    """Devuelve solo lo que no habíamos visto, sin duplicados dentro del lote."""
    items = list(items)
    known_urls, known_pairs = existing_keys(session, items)

    fresh: list[NormalizedOpportunity] = []
    seen_in_batch: set[str] = set()

    for item in items:
        url = str(item.url)
        source_id = source_ids.get(item.source_name)
        pair = (str(source_id), item.external_id)

        if url in known_urls or pair in known_pairs or url in seen_in_batch:
            continue

        seen_in_batch.add(url)
        fresh.append(item)

    return fresh
