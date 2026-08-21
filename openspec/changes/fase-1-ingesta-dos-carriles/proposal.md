# Fase 1 — Ingesta de oportunidades en dos carriles

## Why

Un perfil freelance recién creado tiene dos carencias simultáneas: no llega a
tiempo a los proyectos (el cliente lee las primeras 5-10 propuestas de 20-50) y
no tiene credibilidad (0 reseñas frente a competidores con 50). Automatizar
solo la primera deja la segunda intacta, y sin credibilidad la velocidad no
convierte.

Esta fase construye la ingesta que alimenta ambos frentes: detectar trabajo
pagado en marketplaces, y detectar gente a la que ayudar en foros públicos —
lo segundo produce evidencia pública y verificable de competencia técnica, que
es lo único que sustituye a las reseñas que aún no existen.

Se implementa la ingesta sin IA a propósito: primero hay que demostrar que
entra dato limpio y sin duplicar. Filtrar y clasificar sobre una ingesta que no
funciona es gastar dinero en basura.

## What Changes

- Modelo de datos único (`opportunity`) para los dos carriles, con los campos
  específicos de cada uno como opcionales.
- Cuatro fuentes: Freelancer.com (carril de ventas); GitHub, Stack Exchange y
  Reddit (carril de contribuciones).
- Normalización a un contrato común, deduplicación por dos claves y
  persistencia con registro de resultado (`outcome`) desde el primer día.
- Archivo único de criterio (`config/perfiles.yaml`) separado de los secretos
  (`.env`).
- CLI de operación e inspección, incluido un modo que no escribe en la base.
- Modo `discovery`: captura sin filtrar y sin gastar en IA, para decidir los
  verticales con datos medidos en vez de con intuición.

No se incluye en esta fase: filtrado por reglas, clasificación con IA,
generación de borradores, notificación por Telegram ni reportes. Son fases 2 y 3.

## Capabilities

**New Capabilities**

- `ingesta-oportunidades` — modelo común, normalización, deduplicación,
  persistencia y tolerancia a fallos de una fuente.
- `fuentes-ventas` — obtención de proyectos con intención de pago.
- `fuentes-contribuciones` — obtención de peticiones de ayuda sin responder.
- `configuracion-criterio` — dónde vive el criterio y cómo se cambia sin tocar
  código.
- `cli-operacion` — operación e inspección del sistema desde la terminal.

**Modified Capabilities**

Ninguna: es la primera fase del proyecto.

## Impact

- Nuevo paquete `src/painradar/` con `sources/`, `pipeline/`, `models/`.
- Nueva base de datos SQLite gestionada con Alembic.
- Dependencias nuevas: `httpx`, `pydantic`, `sqlalchemy`, `alembic`,
  `apscheduler`, `structlog`, `pyyaml`, `typer`.
- APIs externas consumidas: Freelancer REST, GitHub REST, Stack Exchange 2.3,
  Reddit OAuth2. Todas oficiales y públicas.
- Ninguna credencial es obligatoria para arrancar: cada fuente sin token se
  omite sola.
