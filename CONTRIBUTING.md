# Cómo contribuir a PainRadar

Gracias por querer ayudar. Esta guía es corta a propósito: lo importante está
en [CLAUDE.md](CLAUDE.md) y en `openspec/specs/`.

## Antes de empezar

- Para algo más que un arreglo pequeño, abre primero un issue y cuenta qué
  quieres cambiar. Así no trabajas en algo que no encaja.
- La fuente de verdad del comportamiento es `openspec/specs/`, no el código.

## Puesta en marcha

```bash
uv sync
cp .env.example .env      # ninguna credencial es obligatoria
uv run alembic upgrade head
uv run pre-commit install
```

## Invariantes que ningún PR puede romper

1. **El sistema nunca postula ni publica solo.** Solo genera borradores para
   revisión humana.
2. **Toda fuente nueva es un adapter** tras el Protocol de
   `src/painradar/sources/base.py`.
3. **Toda oportunidad guardada nace con su fila en `outcome`.**
4. **Los tests no tocan la red.** Usa fixtures grabadas en `tests/fixtures/`.
5. **El criterio vive en `config/perfiles.yaml`**, no en el código.
6. **Los secretos solo en `.env`**, nunca versionados.

## La spec se actualiza con el código

Si tu cambio altera un comportamiento observable, actualiza
`openspec/specs/<capacidad>/spec.md` en el mismo PR. Para trabajo de cierta
entidad, crea un cambio con `openspec new change <nombre>`. Un refactor sin
cambio de comportamiento no toca specs.

## Antes de abrir el PR

```bash
uv run ruff check src/ tests/ scripts/
uv run mypy
uv run pytest
openspec validate --all --strict
```

Todo debe pasar. En el PR explica qué cambia y por qué, y enlaza el issue.

## Licencia

Al contribuir aceptas que tu aporte se publique bajo la [licencia MIT](LICENSE).
