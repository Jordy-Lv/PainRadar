"""Interfaz de línea de comandos de PainRadar."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from painradar.config import get_profiles, get_settings
from painradar.db import create_all, session_scope
from painradar.logging_setup import setup_logging
from painradar.models.enums import Track
from painradar.pipeline.ingest import ingest_source
from painradar.sources import ADAPTERS, build_adapter

app = typer.Typer(
    help="Radar de oportunidades: trabajo pagado (sales) y contribuciones (contrib).",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def _main() -> None:
    setup_logging(get_settings().log_level)


@app.command("init-db")
def init_db() -> None:
    """Crea el esquema de la base de datos."""
    create_all()
    console.print(f"[green]Base de datos lista:[/green] {get_settings().database_url}")


@app.command("sources")
def list_sources() -> None:
    """Lista las fuentes y si tienen credenciales configuradas."""
    table = Table(title="Fuentes")
    table.add_column("Fuente")
    table.add_column("Track")
    table.add_column("Configurada")

    for name in sorted(ADAPTERS):
        adapter = build_adapter(name)
        ok = adapter.is_configured()
        table.add_row(
            name,
            str(adapter.track),
            "[green]sí[/green]" if ok else "[yellow]no[/yellow]",
        )
    console.print(table)


@app.command("fetch")
def fetch(
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Nombre de la fuente")
    ] = None,
    track: Annotated[str | None, typer.Option("--track", "-t", help="sales | contrib")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n")] = 50,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Imprime sin escribir en la base")
    ] = False,
) -> None:
    """Trae oportunidades de una fuente (o de todo un track)."""
    names = _resolve_sources(source, track)
    if not names:
        console.print("[red]Ninguna fuente coincide con el filtro.[/red]")
        raise typer.Exit(code=1)

    asyncio.run(_run_fetch(names, limit=limit, dry_run=dry_run))


async def _run_fetch(names: list[str], *, limit: int, dry_run: bool) -> None:
    for name in names:
        adapter = build_adapter(name)
        try:
            if dry_run:
                # El dry-run abre una sesión igual para no divergir del camino real,
                # pero ingest_source no escribe nada cuando dry_run=True.
                with session_scope() as session:
                    result = await ingest_source(session, adapter, limit=limit, dry_run=True)
            else:
                with session_scope() as session:
                    result = await ingest_source(session, adapter, limit=limit)
        finally:
            await adapter.aclose()

        if not result.ok:
            console.print(f"[yellow]{name}:[/yellow] {result.error}")
            continue

        console.print(
            f"[bold]{name}[/bold]: {result.fetched} traídos, "
            f"{result.new} nuevos, {result.duplicates} duplicados"
        )
        if dry_run:
            _print_items(result.items)


def _print_items(items: list) -> None:  # type: ignore[type-arg]
    table = Table(show_lines=False)
    table.add_column("Publicado", style="dim", no_wrap=True)
    table.add_column("Título", max_width=60)
    table.add_column("Presupuesto / contexto")
    table.add_column("Etiquetas", max_width=30)

    for item in items[:40]:
        context = (
            item.budget_display
            if item.track == Track.SALES
            else f"{item.container or '-'} · {item.engagement_count or 0} resp."
        )
        table.add_row(
            item.published_at.strftime("%m-%d %H:%M"),
            item.title,
            context,
            ", ".join(item.tags[:4]),
        )
    console.print(table)


@app.command("profile")
def show_profile() -> None:
    """Muestra los verticales cargados desde config/perfiles.yaml."""
    profiles = get_profiles()
    table = Table(title="Verticales")
    table.add_column("id")
    table.add_column("keywords", max_width=60)
    table.add_column("tarifa min")
    for vertical in profiles.verticales:
        table.add_row(
            vertical.id,
            ", ".join(vertical.keywords[:8]) + ("..." if len(vertical.keywords) > 8 else ""),
            f"${vertical.tarifa_min_usd:.0f}/h" if vertical.tarifa_min_usd else "-",
        )
    console.print(table)


def _resolve_sources(source: str | None, track: str | None) -> list[str]:
    if source:
        return [source] if source in ADAPTERS else []
    if track:
        wanted = Track(track)
        return [name for name, cls in ADAPTERS.items() if cls.track == wanted]
    return sorted(ADAPTERS)


if __name__ == "__main__":
    app()
