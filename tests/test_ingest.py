"""Ingesta end-to-end contra una base en memoria. Nada toca la red."""

from __future__ import annotations

import httpx
import respx
from sqlalchemy import func, select

from painradar.models import Opportunity, Outcome, Source
from painradar.models.enums import OutcomeStatus, Track
from painradar.pipeline.ingest import ingest_source
from painradar.sources.freelancer import FreelancerAdapter
from tests.conftest import load_fixture

ACTIVE_URL = "https://www.freelancer.com/api/projects/0.1/projects/active/"


def _mock_freelancer() -> None:
    respx.get(ACTIVE_URL).mock(
        return_value=httpx.Response(200, json=load_fixture("freelancer_active_projects"))
    )


@respx.mock
async def test_ingesta_guarda_oportunidades_y_outcomes(session, settings) -> None:
    _mock_freelancer()
    adapter = FreelancerAdapter(settings=settings)

    result = await ingest_source(session, adapter, limit=3)
    await adapter.aclose()
    session.commit()

    assert result.ok
    assert result.fetched == 3
    assert result.new == 3
    assert result.duplicates == 0

    assert session.execute(select(func.count()).select_from(Opportunity)).scalar() == 3
    # Toda oportunidad nace con su fila de outcome: sin eso no hay reporte semanal.
    assert session.execute(select(func.count()).select_from(Outcome)).scalar() == 3
    assert all(o.status == OutcomeStatus.NEW for o in session.execute(select(Outcome)).scalars())

    source = session.execute(select(Source)).scalar_one()
    assert source.name == "freelancer"
    assert source.track == Track.SALES
    assert source.last_success_at is not None


@respx.mock
async def test_segunda_corrida_no_duplica(session, settings) -> None:
    """La verificación clave de la fase 1: correr dos veces no crea basura."""
    _mock_freelancer()

    for _ in range(2):
        adapter = FreelancerAdapter(settings=settings)
        result = await ingest_source(session, adapter, limit=3)
        await adapter.aclose()
        session.commit()

    assert result.fetched == 3
    assert result.new == 0
    assert result.duplicates == 3
    assert session.execute(select(func.count()).select_from(Opportunity)).scalar() == 3


@respx.mock
async def test_dry_run_no_escribe_nada(session, settings) -> None:
    _mock_freelancer()
    adapter = FreelancerAdapter(settings=settings)

    result = await ingest_source(session, adapter, limit=3, dry_run=True)
    await adapter.aclose()
    session.commit()

    assert result.new == 3
    assert len(result.items) == 3
    assert session.execute(select(func.count()).select_from(Opportunity)).scalar() == 0
    assert session.execute(select(func.count()).select_from(Source)).scalar() == 0


@respx.mock
async def test_fuente_sin_credencial_no_tumba_el_ciclo(session) -> None:
    from painradar.config import Settings

    adapter = FreelancerAdapter(settings=Settings(_env_file=None))  # type: ignore[call-arg]
    result = await ingest_source(session, adapter, limit=3)
    await adapter.aclose()

    assert result.ok is False
    assert "no configurada" in (result.error or "")
    assert result.fetched == 0


@respx.mock
async def test_error_http_se_registra_sin_lanzar(session, settings) -> None:
    respx.get(ACTIVE_URL).mock(return_value=httpx.Response(401, text="token inválido"))
    adapter = FreelancerAdapter(settings=settings)

    result = await ingest_source(session, adapter, limit=3)
    await adapter.aclose()

    assert result.ok is False
    assert "401" in (result.error or "")


@respx.mock
async def test_raw_json_se_conserva_para_la_fase_0(session, settings) -> None:
    """La fase 0 mide la demanda con datos crudos: hay que guardarlos."""
    _mock_freelancer()
    adapter = FreelancerAdapter(settings=settings)
    await ingest_source(session, adapter, limit=3)
    await adapter.aclose()
    session.commit()

    opportunity = session.execute(
        select(Opportunity).where(Opportunity.external_id == "38472911")
    ).scalar_one()
    assert opportunity.raw_json["bid_stats"]["bid_count"] == 4
    assert opportunity.tags_json == ["SQL", "PostgreSQL", "Database Administration"]
