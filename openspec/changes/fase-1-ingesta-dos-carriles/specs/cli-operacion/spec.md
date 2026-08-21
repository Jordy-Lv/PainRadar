# Operación por línea de comandos

## Purpose

Dar al usuario control e inspección directos del sistema desde la terminal:
comprobar qué está configurado, verificar qué se está capturando y preparar la
base de datos, sin necesidad de interfaz gráfica.

## ADDED Requirements

### Requirement: Inspección del estado de las fuentes

El sistema SHALL ofrecer un comando que liste todas las fuentes disponibles,
su carril y si tienen credenciales configuradas.

Es la primera comprobación tras clonar el proyecto o tras añadir un token.

#### Scenario: Revisión tras añadir una credencial

- **WHEN** el usuario consulta el estado de las fuentes
- **THEN** obtiene la lista completa indicando carril y si cada una está
  configurada

### Requirement: Inspección del criterio cargado

El sistema SHALL ofrecer un comando que muestre los verticales efectivamente
cargados desde la configuración.

Permite confirmar que un cambio en el criterio se leyó como se esperaba, en
lugar de descubrirlo por el comportamiento.

#### Scenario: Verificación de un cambio de criterio

- **WHEN** el usuario consulta el criterio cargado
- **THEN** obtiene los verticales con sus palabras clave y tarifas mínimas

### Requirement: Ingesta manual selectiva

El sistema SHALL ofrecer un comando de ingesta que permita seleccionar una
fuente concreta o un carril completo, limitar la cantidad de resultados y
ejecutar sin escribir en la base de datos.

#### Scenario: Prueba antes de la primera ingesta real

- **WHEN** el usuario ejecuta la ingesta en modo sin escritura
- **THEN** ve las oportunidades normalizadas y la base de datos no se modifica

#### Scenario: Ingesta de un carril completo

- **WHEN** el usuario ejecuta la ingesta indicando un carril
- **THEN** se ingestan todas las fuentes de ese carril y se informa, por fuente,
  de cuántas se obtuvieron, cuántas eran nuevas y cuántas duplicadas

#### Scenario: Fuente inexistente

- **WHEN** el usuario indica una fuente que no existe
- **THEN** el sistema informa del error y termina con código de salida distinto
  de cero

### Requirement: Preparación del esquema de datos

El sistema SHALL permitir crear y migrar el esquema de la base de datos, y la
migración SHALL tomar la ubicación de la base de datos de la misma
configuración que el resto del sistema.

Tener la URL de la base de datos en dos sitios distintos es una fuente
garantizada de divergencia entre lo migrado y lo usado.

#### Scenario: Primer arranque del proyecto

- **WHEN** el usuario ejecuta la migración en una instalación nueva
- **THEN** el esquema queda creado en la ubicación configurada, creando el
  directorio si no existía
