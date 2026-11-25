# Requerimientos del MVP

Las palabras **debe** y **no debe** expresan comportamiento requerido para el diseño. Prioridad: **MVP** en todos los casos.

## Funcionales

| ID | Requerimiento | Criterio de aceptación |
|---|---|---|
| RF-01 | Debe autenticar usuarios pre-registrados y atribuir cargas y decisiones; no debe ofrecer alta ni roles avanzados. | Un usuario válido accede identificado; credenciales inválidas son rechazadas. |
| RF-02 | Debe aceptar un CSV por lote solo con `template_id` de catálogo y tipo declarado: movimiento o comprobante. | Un ID activo y compatible crea y valida el lote; un ID inexistente, inactivo o incompatible persiste el intento `FALLIDO`, su identificador solicitado y un error de lote consultable, con `plantilla_id NULL`. |
| RF-03 | Debe validar cada fila, conservar errores y distinguir resultado válido, mixto, interpretable sin válidos y fallo estructural/técnico. | Mixto termina `PROCESADO_CON_ERRORES`; cero válidas tras procesar estructura reconocida, `PROCESADO_SIN_VALIDOS`; estructura desconocida o fallo técnico, `FALLIDO`. |
| RF-04 | Debe conservar originales inmutables y separar normalizados y procedencia. | Se consultan ambas representaciones y el original no cambia. |
| RF-05 | Debe admitir solo cobranzas ARS: créditos y comprobantes de venta/cobro con importe decimal positivo. | Débito, moneda distinta de ARS o importe no positivo produce registro `INVALIDO`. |
| RF-06 | Debe reservar la huella solo mientras el lote está en curso o procesado; `FALLIDO` y `DUPLICADO` no reservan. Un conflicto crea directamente un `DUPLICADO` terminal. | Tras un `FALLIDO`, los mismos bytes crean otro lote procesable. En carrera, el perdedor queda `DUPLICADO`; si el dueño falla no se promociona y se requiere otro envío. |
| RF-07 | Debe listar y filtrar pendientes por tipo, lote y estado, con causas conocidas. | Aparece todo registro válido sin conciliación activa y no aparece uno conciliado. |
| RF-08 | Tras un lote con válidos o durante una reversión, debe comparar cada registro habilitado con pendientes opuestos históricos usando ARS, monto exacto y fecha inclusiva de ±3 días. | La pareja que cumple aparece; `PROCESADO_SIN_VALIDOS`, `FALLIDO` y `DUPLICADO` no generan propuestas. |
| RF-09 | Debe conservar la referencia original y usar una copia `ref-nfkd-v1` solo para ordenar y explicar candidatas válidas. | API expone igualdad, Jaccard, diferencia, origen y versiones; el orden es reproducible y una referencia distinta no excluye. |
| RF-10 | Debe mostrar evidencia y exigir confirmación humana para crear una conciliación activa 1:1. | Al confirmar una propuesta libre, esta y ambos registros cambian de estado y se crea la conciliación. |
| RF-11 | Debe exigir motivo al rechazar y conservar actor y fecha. | Con motivo queda `RECHAZADA`; sin motivo se deniega y los registros siguen pendientes. |
| RF-12 | Debe revertir una conciliación activa con motivo, actor y fecha, liberar ambos registros y recompararlos dentro de la misma transacción. | Queda `REVERTIDA`, se crean propuestas nuevas con origen reversión y auditoría; cualquier fallo revierte todo. Sin motivo responde 422; repetición o carrera, 409. |
| RF-13 | Debe consultar una cronología de lotes, errores, propuestas, decisiones y reversiones. | El historial presenta origen, estados, actor, fecha y motivos aplicables sin eliminar eventos. |

## No funcionales

| ID | Requerimiento | Criterio de aceptación |
|---|---|---|
| RNF-01 | Debe garantizar transacciones atómicas, estados permitidos y un protocolo común de bloqueo para propuestas y conciliaciones. | Generación y confirmación bloquean ambos registros por ID ascendente; una carrera deja conciliación activa o propuesta generada compatible, nunca ambas, sin deadlock ni cambios parciales. |
| RNF-02 | Debe representar importes con decimal exacto, nunca punto flotante binario. | Importes equivalentes conservan igualdad exacta y moneda ARS. |
| RNF-03 | Toda propuesta y decisión debe ser explicable, versionada y trazable. | Se identifican score y componentes, regla, normalizador, huella de evaluación, datos, origen `LOTE|REVERSION` y, para acciones humanas, usuario y fecha. |
| RNF-04 | Debe usar datos ficticios o anonimizados, proteger secretos y almacenar contraseñas con hash seguro. | No hay datos personales reales, secretos expuestos ni contraseñas recuperables. |
| RNF-05 | Debe probarse un lote de hasta 10.000 filas sin convertir el resultado en SLA. | La futura prueba completa importación y propuestas y registra tiempos observados sin umbral inventado. |
| RNF-06 | Estados y mensajes deben distinguir válido, mixto, sin válidos, fallido, duplicado, pendiente, propuesto, conciliado y revertido. | El operador reconoce condición y siguiente acción sin inferencias técnicas. |
| RNF-07 | SQL, diccionario, API, CSV, diagramas, glosario y trazabilidad deben compartir estados, errores, origen e invariantes. | La auditoría cruzada encuentra 8 triggers, READMEs en español, rutas sin renombrar y Hugo y Farid responsables en cada etapa. |

Las relaciones con módulos, datos, reglas y diagramas se resumen en la [matriz de trazabilidad](08-matriz-trazabilidad.md).
