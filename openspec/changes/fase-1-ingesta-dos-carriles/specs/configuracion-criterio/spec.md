# Configuración del criterio

## Purpose

Mantener separado lo que cambia a menudo (qué trabajo me interesa) de lo que
cambia poco (el código) y de lo que no debe salir del entorno local (los
secretos), para que ajustar el criterio no requiera programar ni arriesgue una
filtración.

## ADDED Requirements

### Requirement: Separación entre criterio y secretos

El criterio de negocio —verticales, palabras clave, umbrales y objetivos por
fuente— SHALL residir en un archivo de configuración versionado, distinto del
archivo de secretos.

Los secretos (tokens, claves de API, credenciales) SHALL residir únicamente en
variables de entorno y NO SHALL versionarse.

#### Scenario: Ajuste del criterio

- **WHEN** el usuario cambia un umbral o añade palabras clave a un vertical
- **THEN** el cambio surte efecto sin modificar código

#### Scenario: Publicación del repositorio

- **WHEN** el repositorio se publica
- **THEN** el archivo de secretos no forma parte de él y sí existe una plantilla
  de ejemplo sin valores reales

### Requirement: Verticales compartidos entre carriles

Los verticales SHALL definir qué sabe hacer el usuario y SHALL ser compartidos
por los dos carriles; cada vertical incluye sus palabras clave, su ángulo
comercial y su tarifa mínima.

Los umbrales de decisión SHALL definirse por separado para cada carril, porque
el criterio difiere: en ventas se protege el tiempo y el presupuesto, en
contribuciones se protege la reputación y el esfuerzo.

#### Scenario: Detección del vertical de una oportunidad

- **WHEN** se evalúa un texto que coincide con varias palabras clave de un
  vertical
- **THEN** el sistema devuelve el vertical con más coincidencias

#### Scenario: Oportunidad fuera de competencia

- **WHEN** se evalúa un texto que no coincide con ningún vertical
- **THEN** el sistema no devuelve ningún vertical

### Requirement: Arranque sin credenciales

El sistema SHALL arrancar y ser operable sin ninguna credencial configurada.
Cada fuente SHALL declarar por separado si dispone de las suyas.

Esto permite desarrollar, probar y activar las fuentes de forma incremental, a
medida que llegan las cuentas y las aprobaciones.

#### Scenario: Primer arranque sin ningún token

- **WHEN** el usuario arranca el sistema sin configurar credenciales
- **THEN** el sistema funciona y muestra qué fuentes están configuradas y
  cuáles no

### Requirement: Modo descubrimiento

El sistema SHALL soportar un modo de operación que capture todo lo publicado
sin aplicar el filtro de criterio y sin invocar servicios de IA.

Su propósito es medir la demanda real —volumen, presupuestos y competencia por
categoría— antes de fijar el criterio definitivo, en lugar de deducirlo por
intuición.

#### Scenario: Operación en modo descubrimiento

- **WHEN** el sistema opera en modo descubrimiento
- **THEN** captura y almacena las oportunidades sin filtrarlas y sin coste de IA
