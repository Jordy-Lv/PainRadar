# Tareas — Fase 1

## 1. Base del proyecto

- [x] 1.1 Inicializar repositorio y proyecto con `uv`, verificando que `uv sync` instala el entorno
- [x] 1.2 Configurar `ruff`, `mypy --strict`, `pytest` y `pre-commit`, verificando que las tres herramientas pasan en limpio
- [x] 1.3 Definir la plantilla de secretos sin valores reales y excluir el archivo real del control de versiones

## 2. Modelo de datos

- [x] 2.1 Definir el esquema de las cinco tablas, verificando que `mypy --strict` pasa sobre el paquete de modelos
- [x] 2.2 Definir el contrato de oportunidad normalizada con validación, verificando que rechaza URLs inválidas
- [x] 2.3 Generar y aplicar la migración inicial, verificando con `alembic current` y la lista de tablas creadas

## 3. Configuración

- [x] 3.1 Cargar secretos desde variables de entorno, verificando que el sistema arranca sin ninguna definida
- [x] 3.2 Cargar y validar el archivo de criterio, verificando con el test que comprueba los tres verticales y los umbrales de ambos carriles
- [x] 3.3 Implementar la detección de vertical por coincidencia de palabras clave, verificando que elige el de más coincidencias y que devuelve vacío fuera de competencia

## 4. Fuentes

- [x] 4.1 Definir el contrato de fuente y la base HTTP con reintentos, verificando que respeta el tiempo de espera indicado por la API
- [x] 4.2 Implementar la fuente de Freelancer.com, verificando que envía el encabezado de autenticación y pide descripción completa y datos del cliente
- [x] 4.3 Implementar la fuente de GitHub, verificando que descarta pull requests y deduplica entre consultas
- [x] 4.4 Implementar la fuente de Stack Exchange, verificando que pide preguntas sin responder y devuelve el enunciado en texto plano
- [x] 4.5 Implementar la fuente de Reddit, verificando que obtiene credencial antes de leer y descarta publicaciones fijadas

## 5. Pipeline de ingesta

- [x] 5.1 Implementar la deduplicación por doble clave, verificando que la segunda ejecución no crea nada nuevo
- [x] 5.2 Implementar la persistencia con registro de resultado, verificando que cada oportunidad guardada tiene el suyo en estado inicial
- [x] 5.3 Implementar el aislamiento de fallos por fuente, verificando que ni una credencial ausente ni un error HTTP lanzan excepción
- [x] 5.4 Implementar el modo sin escritura, verificando que la base de datos queda intacta

## 6. Operación

- [x] 6.1 Implementar los comandos de estado de fuentes, criterio cargado, ingesta y preparación del esquema, verificando su ejecución manual
- [x] 6.2 Implementar el registro estructurado, verificando que emite JSON fuera de terminal interactiva

## 7. Verificación de la fase

- [x] 7.1 Verificar la suite completa sin acceso a red: `uv run pytest` en verde
- [x] 7.2 Verificar calidad estática: `ruff check` y `mypy` sin hallazgos
- [x] 7.3 Escribir el script de grabación de fixtures reales, pendiente de ejecutar cuando existan credenciales

## 8. Pendiente de credenciales (no bloquea la fase)

- [ ] 8.1 Regrabar las fixtures contra respuestas reales de cada API y confirmar que los tests siguen en verde
- [ ] 8.2 Verificar la ingesta real contra Freelancer.com y confirmar que una segunda ejecución no duplica
