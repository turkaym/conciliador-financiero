# Requerimientos del MVP

Las palabras **debe** y **no debe** expresan comportamiento requerido para el diseño. Prioridad: **MVP** en todos los casos.

## Funcionales

| ID | Requerimiento | Criterio de aceptación |
|---|---|---|
| RF-01 | Debe autenticar usuarios pre-registrados y atribuir cargas y decisiones; no debe ofrecer alta ni roles avanzados. | Un usuario válido accede identificado; credenciales inválidas son rechazadas. |
| RF-02 | Debe aceptar un CSV por lote solo con `template_id` de catálogo y tipo declarado: movimiento o comprobante. | Un ID activo y compatible crea y valida el lote; un ID inexistente, inactivo o incompatible persiste el intento `FALLIDO`, su identificador solicitado y un error de lote consultable, con `plantilla_id NULL`. |
| RF-03 | Debe validar cada fila, conservar errores por lote, registro y campo, procesar las válidas y excluir las inválidas de propuestas. | Un lote mixto termina `PROCESADO_CON_ERRORES`; válidas e inválidas quedan diferenciadas y consultables. |
| RF-04 | Debe conservar originales inmutables y separar normalizados y procedencia. | Se consultan ambas representaciones y el original no cambia. |
| RF-05 | Debe admitir solo cobranzas ARS: créditos y comprobantes de venta/cobro con importe decimal positivo. | Débito, moneda distinta de ARS o importe no positivo produce registro `INVALIDO`. |
| RF-06 | Debe detectar archivo repetido por huella y fila repetida por ID externo o huella estable de originales. Todo primer intento no `DUPLICADO`, incluso uno `FALLIDO` por plantilla desconocida, reserva la huella. | Todo envío posterior de los mismos bytes queda `DUPLICADO`, referencia el primer lote y no crea filas; una fila repetida queda inválida sin bloquear las otras. |
| RF-07 | Debe listar y filtrar pendientes por tipo, lote y estado, con causas conocidas. | Aparece todo registro válido sin conciliación activa y no aparece uno conciliado. |
| RF-08 | Al finalizar un lote `PROCESADO` o `PROCESADO_CON_ERRORES`, debe comparar automáticamente cada nuevo elegible con todos los pendientes elegibles opuestos, incluso de lotes anteriores, usando ARS, monto exacto y fecha inclusiva de ±3 días. | La pareja que cumple aparece; fallar un criterio la excluye. Lotes `FALLIDO` o `DUPLICADO` no generan propuestas. |
| RF-09 | Debe conservar la referencia original y usar una copia `ref-nfkd-v1` solo para ordenar y explicar candidatas válidas. | API expone igualdad, Jaccard, diferencia, origen y versiones; el orden es reproducible y una referencia distinta no excluye. |
| RF-10 | Debe mostrar evidencia y exigir confirmación humana para crear una conciliación activa 1:1. | Al confirmar una propuesta libre, esta y ambos registros cambian de estado y se crea la conciliación. |
| RF-11 | Debe exigir motivo al rechazar y conservar actor y fecha. | Con motivo queda `RECHAZADA`; sin motivo se deniega y los registros siguen pendientes. |
| RF-12 | Debe revertir una conciliación activa solo con motivo, actor y fecha, sin borrar decisiones. | Queda `REVERTIDA` y los registros vuelven a pendientes; sin motivo o repetición se deniega. |
| RF-13 | Debe consultar una cronología de lotes, errores, propuestas, decisiones y reversiones. | El historial presenta origen, estados, actor, fecha y motivos aplicables sin eliminar eventos. |

## No funcionales

| ID | Requerimiento | Criterio de aceptación |
|---|---|---|
| RNF-01 | Debe garantizar transacciones atómicas, estados permitidos y un protocolo común de bloqueo para propuestas y conciliaciones. | Generación y confirmación bloquean ambos registros por ID ascendente; una carrera deja conciliación activa o propuesta generada compatible, nunca ambas, sin deadlock ni cambios parciales. |
| RNF-02 | Debe representar importes con decimal exacto, nunca punto flotante binario. | Importes equivalentes conservan igualdad exacta y moneda ARS. |
| RNF-03 | Toda propuesta y decisión debe ser explicable, versionada y trazable. | Se identifican score y componentes, regla, normalizador, datos, origen y, para acciones humanas, usuario y fecha. |
| RNF-04 | Debe usar datos ficticios o anonimizados, proteger secretos y almacenar contraseñas con hash seguro. | No hay datos personales reales, secretos expuestos ni contraseñas recuperables. |
| RNF-05 | Debe probarse un lote de hasta 10.000 filas sin convertir el resultado en SLA. | La futura prueba completa importación y propuestas y registra tiempos observados sin umbral inventado. |
| RNF-06 | Estados y mensajes deben distinguir válido, inválido, pendiente, propuesto, conciliado y revertido. | El operador reconoce condición y siguiente acción sin inferencias técnicas. |

Las relaciones con módulos, datos, reglas y diagramas se resumen en la [matriz de trazabilidad](08-matriz-trazabilidad.md).
