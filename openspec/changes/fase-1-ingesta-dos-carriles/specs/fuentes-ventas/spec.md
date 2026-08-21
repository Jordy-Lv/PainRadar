# Fuentes del carril de ventas

## Purpose

Obtener, en el menor tiempo posible desde su publicación, proyectos en los que
la intención de pago está garantizada por construcción: si alguien los publicó
en un marketplace, es porque quiere contratar.

## ADDED Requirements

### Requirement: Obtención de proyectos activos de Freelancer.com

El sistema SHALL obtener proyectos activos mediante la API REST oficial de
Freelancer.com, autenticándose con el token OAuth2 del usuario.

La petición SHALL solicitar explícitamente la descripción completa, las
categorías del proyecto y los datos del cliente (país, verificación de pago y
reputación). Sin esos datos, las fases posteriores no pueden juzgar ni el
encaje técnico ni la fiabilidad del cliente.

#### Scenario: Obtención autenticada

- **WHEN** el sistema consulta proyectos activos con un token configurado
- **THEN** la petición viaja autenticada y solicita descripción completa y
  datos del cliente

#### Scenario: Token ausente

- **WHEN** no hay token configurado
- **THEN** la fuente se reporta como no configurada y no se realiza ninguna
  petición

### Requirement: Datos necesarios para decidir una postulación

De cada proyecto, el sistema SHALL obtener el presupuesto (mínimo, máximo,
moneda y si es por horas), el número de propuestas ya recibidas y, cuando la
plataforma lo exponga, el país del cliente, su reputación y si tiene método de
pago verificado.

El número de propuestas existentes es la medida directa de si aún se llega a
tiempo; la verificación de pago es la señal más barata para descartar clientes
problemáticos.

#### Scenario: Proyecto de presupuesto fijo

- **WHEN** se normaliza un proyecto de presupuesto fijo
- **THEN** la oportunidad recoge mínimo, máximo, moneda, marca de no-horario y
  número de propuestas recibidas

#### Scenario: Proyecto por horas de un cliente sin verificar

- **WHEN** se normaliza un proyecto por horas cuyo cliente no tiene método de
  pago verificado
- **THEN** la oportunidad queda marcada como horaria y con la verificación de
  pago en negativo

### Requirement: Respeto de los límites de la API

Ante una respuesta de límite de peticiones excedido o un error temporal del
servidor, el sistema SHALL reintentar con espera exponencial y SHALL respetar
el tiempo indicado por la API cuando esta lo especifique.

Pelearse con el límite de una API oficial es la vía más rápida a perder el
acceso, que es el único activo insustituible de este carril.

#### Scenario: La API pide esperar

- **WHEN** la API responde que se excedió el límite de peticiones e indica
  cuánto esperar
- **THEN** el sistema espera ese tiempo, reintenta y completa la obtención

#### Scenario: Reintentos agotados

- **WHEN** los reintentos se agotan sin respuesta válida
- **THEN** el sistema reporta el fallo de esa fuente sin interrumpir las demás

### Requirement: Entorno de pruebas seleccionable

El sistema SHALL permitir apuntar a la API de pruebas de la plataforma en lugar
de la de producción mediante configuración, sin cambios en el código.

#### Scenario: Configuración de entorno de pruebas

- **WHEN** se configura el entorno como pruebas
- **THEN** las peticiones se dirigen al servidor de pruebas de la plataforma
