# Ingesta de oportunidades

## Purpose

Convertir lo que publican fuentes heterogéneas (marketplaces, foros, issues) en
un flujo único de oportunidades normalizadas, sin duplicados y con su
resultado registrado, de forma que el resto del sistema no necesite saber de
dónde vino cada una.

## ADDED Requirements

### Requirement: Contrato común de oportunidad

El sistema SHALL representar toda oportunidad, sea del carril que sea, con un
único contrato de datos que incluya fuente, carril, identificador externo, URL,
título, descripción, autor, etiquetas y fecha de publicación.

Los campos exclusivos de un carril (presupuesto, número de propuestas y datos
del cliente en ventas; contenedor, número de respuestas y puntuación en
contribuciones) SHALL ser opcionales, de modo que una fuente que no los tenga
no quede obligada a inventarlos.

#### Scenario: Proyecto de marketplace normalizado

- **WHEN** una fuente del carril de ventas entrega un proyecto con presupuesto
  y datos del cliente
- **THEN** el sistema produce una oportunidad con los campos comunes rellenos,
  los campos de ventas rellenos y los de contribuciones vacíos

#### Scenario: Petición de ayuda normalizada

- **WHEN** una fuente del carril de contribuciones entrega una pregunta sin
  responder
- **THEN** el sistema produce una oportunidad con los campos comunes rellenos,
  el contenedor y el recuento de respuestas rellenos, y los campos de
  presupuesto vacíos

### Requirement: Conservación de la respuesta original

El sistema SHALL conservar la respuesta cruda de la fuente junto a cada
oportunidad guardada.

Sin esto no es posible re-normalizar tras corregir un error de interpretación,
ni analizar la demanda con campos que no se habían previsto, sin volver a
consultar la API — que para entonces ya no devuelve lo mismo.

#### Scenario: Análisis posterior sobre datos no previstos

- **WHEN** se guarda una oportunidad
- **THEN** la respuesta original de la fuente queda almacenada íntegra y
  consultable

### Requirement: Deduplicación por doble clave

El sistema SHALL descartar toda oportunidad ya conocida, identificándola tanto
por su URL como por el par (fuente, identificador externo).

Ninguna de las dos claves basta por sí sola: el par identifica la oportunidad
dentro de su plataforma, y la URL detecta la misma oportunidad llegada por dos
caminos distintos.

El sistema SHALL deduplicar también dentro de un mismo lote, porque una fuente
puede devolver el mismo elemento en varias consultas.

#### Scenario: Segunda ejecución sobre datos idénticos

- **WHEN** se ejecuta la ingesta dos veces seguidas y la fuente devuelve lo mismo
- **THEN** la segunda ejecución no crea ninguna oportunidad nueva y las reporta
  todas como duplicadas

#### Scenario: Elemento repetido dentro de un mismo lote

- **WHEN** una fuente devuelve el mismo elemento en dos consultas del mismo ciclo
- **THEN** el sistema lo guarda una sola vez

### Requirement: Registro de resultado desde el origen

El sistema SHALL crear un registro de resultado en estado inicial para cada
oportunidad guardada, en la misma operación.

El registro de resultado es lo que después permite medir qué rinde y ajustar el
criterio con datos. Crearlo más tarde significa perder el histórico de todo lo
capturado antes de esa decisión.

#### Scenario: Oportunidad recién capturada

- **WHEN** se guarda una oportunidad nueva
- **THEN** existe su registro de resultado asociado en estado inicial

### Requirement: Aislamiento de fallos entre fuentes

Un fallo de una fuente —error de red, error HTTP, credencial ausente— SHALL
quedar registrado y reportado sin interrumpir el ciclo de las demás fuentes.

Una fuente sin credencial configurada SHALL tratarse como fase no activada y no
como error.

#### Scenario: Credencial ausente

- **WHEN** se ejecuta la ingesta de una fuente sin su credencial
- **THEN** el sistema informa de que no está configurada, no lanza excepción y
  continúa con las demás fuentes

#### Scenario: La API responde con error

- **WHEN** una fuente devuelve un error HTTP no recuperable
- **THEN** el sistema registra el error en el resultado de esa fuente y el
  proceso termina sin excepción

### Requirement: Ejecución sin escritura

El sistema SHALL ofrecer un modo de ejecución que obtenga y normalice
oportunidades sin escribir nada en la base de datos.

#### Scenario: Comprobación previa a la primera ingesta real

- **WHEN** se ejecuta la ingesta en modo sin escritura
- **THEN** se obtienen y muestran las oportunidades normalizadas y la base de
  datos queda sin modificar
