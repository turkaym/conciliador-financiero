# Matriz de trazabilidad

La matriz permite revisar cobertura sin duplicar criterios completos. Los detalles canónicos están en [requerimientos](02-requerimientos.md), [reglas](03-reglas-de-negocio.md) y [diccionario](05-diccionario-de-datos.md).

## Trazabilidad funcional cruzada

| Requisitos | Reglas | Módulo | Entidades principales | Diagramas | Evidencia de aceptación |
|---|---|---|---|---|---|
| RF-01; RNF-04 | RN-08 | Acceso básico | `usuario`, `evento_historial` | Contexto, casos de uso | Autenticación positiva/negativa y atribución sin datos reales |
| RF-02–RF-06; RNF-02, RNF-06 | RN-10–RN-12 | Catálogos, importación, validación-normalización | `fuente_datos`, `plantilla_importacion`, `campo_plantilla`, `lote_carga`, registros y errores | Actividad, secuencia, ER, lógico, estados | [Diez CSV](csv/README.md): válido, mixto, cero válidos, estructural, duplicado y recarga tras fallo |
| RF-07; RNF-06 | RN-01 | Pendientes-consultas | `registro_importado`, subtipos | Casos de uso, estados | Filtros distinguen condición, causa y siguiente acción |
| RF-08–RF-09; RNF-03 | RN-01, RN-03–RN-05, RN-07, RN-13 | Propuestas | subtipos, `propuesta_conciliacion` | Módulos, secuencia, wireframe 05 | API explica huella, score, versiones y origen XOR; rechazo idéntico queda suprimido |
| RF-10–RF-12; RNF-01 | RN-02, RN-05–RN-09, RN-12–RN-13 | Revisión-conciliación | propuesta, conciliación, registros y eventos | Secuencia, estados, ER, wireframe 06 | Locks `id ASC`, recomparación inmediata, exclusión de pareja idéntica, rollback y cero deadlocks |
| RF-13; RNF-03 | RN-08–RN-09 | Trazabilidad | `evento_historial` y entidades referenciadas | Contexto, módulos, ER | Cronología conserva origen, actor, fecha y motivo |
| Volumen (RNF-05) | — | Importación, propuestas | `lote_carga`, registros y propuestas | Actividad, secuencia | Prueba futura de 10.000 filas documentada sin umbral de servicio |
| Coherencia (RNF-07) | RN-13 | Todos | 12 tablas, 106 columnas, 109 constraints, 52 índices, 8 triggers | Todas las vistas | SQL, diccionario, API, CSV, SVG, glosario y READMEs coinciden |

## Cobertura de la consigna docente

| Aspecto solicitado | Evidencia documental |
|---|---|
| Alcance, prioridades y módulos | [Alcance y módulos](01-alcance-y-modulos.md) separa MVP, opcionales y exclusiones |
| Requisitos verificables | [Requerimientos](02-requerimientos.md) contiene 13 RF y 7 RNF, todos con prioridad y aceptación |
| Reglas y estados | [Reglas](03-reglas-de-negocio.md) contiene 13 reglas y las máquinas de estado |
| Diseño conceptual, lógico y físico | [Diseño](04-diseno-base-de-datos.md), [diccionario](05-diccionario-de-datos.md), diagramas ER y lógico |
| Actores, comportamiento y arquitectura | Diagramas de contexto, casos de uso, actividad, módulos y secuencia en [diagramas](06-diagramas.md) |
| Decisiones, alternativas, riesgos y supuestos | [Decisiones y supuestos](07-decisiones-y-supuestos.md) |
| Lenguaje común y navegación | [Glosario](glosario.md), índice y enlaces locales |
| Esqueletos modulares | [Backend](../../backend/README.md) y [frontend](../../frontend/README.md), solo READMEs |
| Infraestructura y DDL | [Compose](../../docker-compose.yml), [SQL y guía PostgreSQL 16](../../database/README.md) |
| Contrato invocable | [API `/api/v1`](09-contrato-api.md) con requests, responses, errores y paginación |
| Experiencia | [Seis wireframes SVG](wireframes/README.md) con estados y navegación |

## Comprobación de cobertura

Cada grupo remite a un criterio canónico, un módulo, datos y al menos un diagrama. La aceptación del producto es futura: esta matriz prueba completitud documental, no ejecución de software.
