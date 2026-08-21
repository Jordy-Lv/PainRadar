from __future__ import annotations

from painradar.config import Profiles, Settings


def test_perfiles_cargan_los_tres_verticales(profiles: Profiles) -> None:
    assert [v.id for v in profiles.verticales] == ["datos", "automatizacion", "backend"]
    assert profiles.sales.filtros.presupuesto_min_usd == 100
    assert profiles.contrib.filtros.solo_sin_responder is True
    assert "stackoverflow" in profiles.contrib.stackexchange.sites


def test_match_vertical_elige_el_de_mas_coincidencias(profiles: Profiles) -> None:
    vertical = profiles.match_vertical(
        "Migración de SQL Server a Postgres con ETL", "necesito un data pipeline"
    )
    assert vertical is not None
    assert vertical.id == "datos"


def test_match_vertical_devuelve_none_si_no_es_lo_mio(profiles: Profiles) -> None:
    assert profiles.match_vertical("Diseño de logo para cafetería") is None


def test_base_url_cambia_con_el_entorno() -> None:
    prod = Settings(_env_file=None, freelancer_env="prod")  # type: ignore[call-arg]
    sandbox = Settings(_env_file=None, freelancer_env="sandbox")  # type: ignore[call-arg]

    assert prod.freelancer_base_url == "https://www.freelancer.com/api"
    assert "sandbox" in sandbox.freelancer_base_url
