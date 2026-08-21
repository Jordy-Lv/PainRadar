# Diseño — Fase 1

## Context

Ver `proposal.md` — Why. Restricción dominante: el proyecto arranca sin ninguna
credencial. Las cuentas de marketplace requieren verificación y la API de
Upwork tiene ~1 semana de revisión, así que el diseño tiene que permitir
desarrollar, probar y activar fuentes por separado, sin que la ausencia de una
bloquee a las demás.

## Goals / Non-Goals

**Goals**

- Que añadir una fuente no obligue a tocar nada aguas abajo.
- Que la ausencia o el fallo de una fuente no degrade a las demás.
- Que los tests corran sin red y sin credenciales.

**Non-Goals**

- Rendimiento y concurrencia: el volumen es de decenas de elementos por ciclo.
- Base de datos multiusuario: es una herramienta personal.
- Cualquier forma de publicación automática, en esta fase y en todas.

## Decisions

**Un solo modelo `opportunity` para los dos carriles, no dos tablas.**
Un proyecto de Freelancer y un issue de GitHub comparten estructura —algo que
alguien publicó, que puedo resolver, donde llegar temprano importa— y difieren
solo en un puñado de campos. Dos tablas obligarían a duplicar dedupe,
resultados y reportes. Alternativa descartada: herencia de tablas, que en
SQLite complica las consultas sin aportar nada aquí. El coste aceptado es
tener columnas nulas según el carril, explícitamente agrupadas y comentadas.

**Cliente HTTP propio en lugar del SDK oficial de Freelancer.**
El SDK sigue declarando soporte de Python 2.7 y arrastra dependencias sin
mantenimiento. La API es REST plana: reimplementarla son ~50 líneas frente a
adoptar una dependencia muerta en el núcleo del sistema.

**Fetching asíncrono, persistencia síncrona.**
La latencia está en la red, no en el disco: escribir en un SQLite local tarda
microsegundos. Hacer async también la capa de datos añadiría una dependencia y
complejidad de sesiones a cambio de nada medible.

**Guardar la respuesta cruda de cada oportunidad.**
Duplica el almacenamiento, que a este volumen es irrelevante. A cambio permite
re-normalizar tras corregir un error de interpretación y analizar campos que no
se habían previsto, sin volver a una API que ya no devolverá lo mismo. Es la
materia prima del modo descubrimiento.

**Deduplicar por dos claves, no por hash del contenido.**
Los títulos y descripciones se editan tras publicarse; un hash del contenido
generaría duplicados en cuanto el autor corrigiera una errata.

**Crear el registro de resultado junto a la oportunidad, no al notificar.**
Es lo que permite medir qué rinde. Añadirlo en la fase 2 significaría no tener
histórico de todo lo capturado durante la fase de descubrimiento, que es
justamente el periodo que hay que medir.

**El filtro por estrellas de GitHub vive en el pipeline, no en el adapter.**
La API de búsqueda de issues no admite filtrar por estrellas del repositorio.
Resolverlo en el adapter costaría una petición por issue; en el pipeline se
resuelve con una caché de repositorios. Se implementa en la fase 2, cuando
exista el filtro de reglas.

## Risks / Trade-offs

- **Las fixtures se escribieron siguiendo la forma documentada de cada API, no
  grabadas de respuestas reales** → los tests verifican la lógica de
  normalización, no que la API responda como se cree. Mitigación: script de
  grabación de fixtures reales, a ejecutar en cuanto haya credenciales; es lo
  único que detecta un cambio de API silencioso.
- **Cuota de Stack Exchange**: el diseño gasta ~3.200 peticiones diarias de las
  10.000 disponibles con clave registrada; sin clave son 300 y se agota en el
  primer ciclo → el adapter registra la cuota restante en cada ciclo y la
  documentación marca la clave como necesaria en la práctica.
- **Columnas nulas según el carril** → agrupadas y comentadas por carril; el
  contrato de datos las declara opcionales de forma explícita.
- **Reddit responde con límite excedido a agentes genéricos** → identificación
  descriptiva obligatoria en la configuración.

## Migration Plan

Primera fase del proyecto: no hay datos previos que migrar. El esquema se crea
con una única migración. Retroceder es borrar el archivo de base de datos.

## Open Questions

- Qué intervalo real de sondeo aguanta cada fuente sin acercarse a su límite.
  Se responde con datos de operación; no cambia el diseño porque el intervalo
  ya es configurable por fuente.
