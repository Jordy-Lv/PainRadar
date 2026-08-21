# Convenciones de PainRadar

## Regla nº 1 — La spec se actualiza con el código

Después de **cualquier** cambio de código, actualizar la documentación OpenSpec
en el mismo turno. No es opcional ni hay que pedirlo.

```bash
openspec validate --all --strict    # debe pasar antes de dar nada por cerrado
```

- Cambio de comportamiento observable → actualizar `openspec/specs/<capacidad>/spec.md`.
- Trabajo nuevo de cierta entidad → `openspec new change <nombre>`, escribir sus
  artefactos, implementar, sincronizar a los specs principales.
- Refactor sin cambio de comportamiento → no toca specs (marcar `skip_specs`).

Una spec desactualizada es peor que no tener spec: deja de ser la fuente de
verdad y el código pasa a ser la única referencia real, que es justo lo que
este método existe para evitar.

## Invariantes que ningún cambio puede romper

1. **El sistema nunca postula ni publica solo.** Solo genera borradores para
   revisión humana. En ventas, postular automáticamente lleva a la suspensión;
   en contribuciones, publicar automáticamente destruye la reputación que ese
   carril existe para construir.
2. **Toda fuente nueva es un adapter tras el Protocol de `sources/base.py`.**
   El pipeline aguas abajo no cambia al añadir una fuente.
3. **Toda oportunidad guardada nace con su fila en `outcome`.** Sin eso no hay
   forma de medir qué rinde ni de ajustar el criterio con datos.
4. **Los tests no tocan la red.** Se usan fixtures grabadas.
5. **El criterio vive en `config/perfiles.yaml`.** Cambiarlo no debe requerir
   tocar código.
6. **Los secretos solo en `.env`**, nunca versionados.

## Verificación antes de cerrar cualquier trabajo

```bash
uv run ruff check src/ tests/ scripts/
uv run mypy
uv run pytest
openspec validate --all --strict
```

## Estructura

| Ruta | Qué contiene |
|---|---|
| `src/painradar/sources/` | Un adapter por fuente, aislados tras un Protocol |
| `src/painradar/pipeline/` | Normalizar → deduplicar → guardar |
| `src/painradar/models/` | Tablas SQLAlchemy + contratos Pydantic |
| `config/perfiles.yaml` | El criterio: verticales y umbrales por carril |
| `openspec/specs/` | Qué hace el sistema (fuente de verdad) |
| `openspec/changes/` | Cambios en curso |
