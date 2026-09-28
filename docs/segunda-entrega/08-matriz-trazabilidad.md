# Matriz de trazabilidad

La matriz permite revisar cobertura sin duplicar criterios completos. Los detalles canónicos están en [requerimientos](02-requerimientos.md), [reglas](03-reglas-de-negocio.md) y [diccionario](05-diccionario-de-datos.md).

## Trazabilidad funcional cruzada

| Requisitos | Reglas | Módulo | Entidades principales | Diagramas | Evidencia de aceptación |
|---|---|---|---|---|---|
| RF-01; RNF-04 | RN-08 | Acceso básico | `usuario`, `evento_historial` | Contexto, casos de uso | Autenticación positiva/negativa y atribución sin datos reales |
| RF-02–RF-06; RNF-02 | RN-10–RN-12 | Catálogos, importación, validación-normalización | `fuente_datos`, `plantilla_importacion`, `campo_plantilla`, `lote_carga`, `registro_importado`, subtipos, `error_validacion` | Actividad, secuencia, ER, lógico, estados | Lotes válido, mixto, estructural y duplicado; originales y decimales conservados |
| RF-07; RNF-06 | RN-01 | Pendientes-consultas | `registro_importado`, subtipos | Casos de uso, estados | Filtros distinguen condición, causa y siguiente acción |
| RF-08–RF-09; RNF-03 | RN-01, RN-03–RN-05, RN-07 | Propuestas | subtipos, `propuesta_conciliacion` | Módulos, secuencia | Solo parejas elegibles; referencia explica y no habilita |
| RF-10–RF-12; RNF-01 | RN-02, RN-05–RN-09, RN-12 | Revisión-conciliación | `propuesta_conciliacion`, `conciliacion`, `evento_historial` | Secuencia, estados, ER | Confirmación 1:1 concurrente; rechazo y reversión con motivo, sin cambios parciales |
| RF-13; RNF-03 | RN-08–RN-09 | Trazabilidad | `evento_historial` y entidades referenciadas | Contexto, módulos, ER | Cronología conserva origen, actor, fecha y motivo |
| Volumen (RNF-05) | — | Importación, propuestas | `lote_carga`, registros y propuestas | Actividad, secuencia | Prueba futura de 10.000 filas documentada sin umbral de servicio |

## Cobertura de la consigna docente

| Aspecto solicitado | Evidencia documental |
|---|---|
| Alcance, prioridades y módulos | [Alcance y módulos](01-alcance-y-modulos.md) separa MVP, opcionales y exclusiones |
| Requisitos verificables | [Requerimientos](02-requerimientos.md) contiene 13 RF y 6 RNF, todos con prioridad y aceptación |
| Reglas y estados | [Reglas](03-reglas-de-negocio.md) contiene 12 reglas y las máquinas de estado |
| Diseño conceptual, lógico y físico | [Diseño](04-diseno-base-de-datos.md), [diccionario](05-diccionario-de-datos.md), diagramas ER y lógico |
| Actores, comportamiento y arquitectura | Diagramas de contexto, casos de uso, actividad, módulos y secuencia en [diagramas](06-diagramas.md) |
| Decisiones, alternativas, riesgos y supuestos | [Decisiones y supuestos](07-decisiones-y-supuestos.md) |
| Lenguaje común y navegación | [Glosario](glosario.md), índice y enlaces locales |

## Comprobación de cobertura

Cada grupo remite a un criterio canónico, un módulo, datos y al menos un diagrama. La aceptación seguiría siendo futura: esta matriz prueba completitud documental, no ejecución de software.
