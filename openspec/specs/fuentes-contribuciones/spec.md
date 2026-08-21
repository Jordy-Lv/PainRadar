# Fuentes del carril de contribuciones

## Purpose

Encontrar preguntas y problemas técnicos reales, recientes y todavía sin
responder, que el usuario pueda resolver — para construir en abierto la
evidencia pública de competencia que un perfil freelance nuevo no tiene y no
puede comprar.

## Requirements

### Requirement: Prioridad a lo que aún no tiene respuesta

Las fuentes de este carril SHALL priorizar peticiones sin respuesta alguna y
SHALL descartar aquellas que superen el número máximo de respuestas
configurado.

El valor de una contribución cae en picado cuando el hilo ya tiene actividad:
la respuesta llega tarde, se pierde entre otras y no deja rastro atribuible.

#### Scenario: Pregunta sin responder

- **WHEN** una fuente encuentra una pregunta reciente sin ninguna respuesta
- **THEN** la oportunidad se incluye, marcada como no respondida

#### Scenario: Hilo con actividad previa

- **WHEN** una publicación ya acumula respuestas y la configuración exige que no
  las tenga
- **THEN** la oportunidad se descarta

### Requirement: Ventana temporal configurable

Las fuentes de este carril SHALL limitar la búsqueda a lo publicado dentro de
la ventana de antigüedad máxima configurada.

#### Scenario: Búsqueda acotada en el tiempo

- **WHEN** se construye la consulta a la fuente
- **THEN** incluye la restricción temporal derivada de la antigüedad máxima
  configurada

### Requirement: Issues de GitHub sin asignar

El sistema SHALL obtener issues abiertos, sin persona asignada, filtrados por
las etiquetas y los lenguajes configurados.

El sistema SHALL descartar las pull requests que la búsqueda devuelva mezcladas
con los issues: una pull request ajena no es una oportunidad de contribuir.

El sistema SHALL identificar el repositorio de cada issue.

#### Scenario: Issue abierto y sin asignar

- **WHEN** la búsqueda devuelve un issue abierto sin asignar
- **THEN** la oportunidad recoge el repositorio, el recuento de comentarios y
  las etiquetas

#### Scenario: La búsqueda devuelve una pull request

- **WHEN** la búsqueda devuelve una pull request junto a los issues
- **THEN** el sistema la descarta

#### Scenario: Mismo issue en varias consultas

- **WHEN** varias consultas de un mismo ciclo devuelven el mismo issue
- **THEN** aparece una sola vez en el resultado

### Requirement: Preguntas de Stack Exchange sin responder

El sistema SHALL obtener preguntas sin ninguna respuesta, de los sitios y
etiquetas configurados, con su enunciado completo en texto plano.

El sistema SHALL registrar la cuota de peticiones restante que informa la API en
cada ciclo, para que el agotamiento de cuota sea visible antes de causar un
fallo silencioso.

#### Scenario: Pregunta obtenida con su cuerpo

- **WHEN** se normaliza una pregunta
- **THEN** su descripción queda en texto plano, sin marcado HTML ni entidades
  escapadas

#### Scenario: Identificación entre sitios

- **WHEN** se normalizan preguntas de varios sitios de la red
- **THEN** cada oportunidad queda identificada de forma única incluyendo su
  sitio de origen

### Requirement: Publicaciones recientes de Reddit

El sistema SHALL obtener las publicaciones recientes de los subreddits
configurados mediante la API oficial autenticada, renovando su credencial de
acceso antes de que expire.

El sistema SHALL descartar publicaciones fijadas y publicaciones marcadas para
adultos.

#### Scenario: Autenticación previa a la lectura

- **WHEN** el sistema va a leer publicaciones y no tiene credencial de acceso
  vigente
- **THEN** la obtiene antes de realizar cualquier lectura

#### Scenario: Publicación fijada por moderación

- **WHEN** la fuente devuelve una publicación fijada
- **THEN** el sistema la descarta

### Requirement: Ninguna publicación automática

El sistema SHALL limitarse a leer las fuentes de este carril. NO SHALL publicar
comentarios, respuestas ni contribuciones de ningún tipo de forma automática.

Una respuesta automática se detecta al instante y destruye exactamente la
reputación que este carril existe para construir.

#### Scenario: Oportunidad de contribución detectada

- **WHEN** el sistema detecta una oportunidad de contribuir
- **THEN** la registra para revisión humana y no realiza ninguna escritura
  contra la plataforma de origen
