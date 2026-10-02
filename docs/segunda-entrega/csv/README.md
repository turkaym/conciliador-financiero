# Contrato CSV y casos ficticios

Estos archivos UTF-8 sin BOM son evidencia documental para RF-02–RF-06 y RN-10–RN-11. Usan coma, salto de línea estándar, fechas ISO `YYYY-MM-DD`, decimal con punto, moneda `ARS` y datos inventados. Ninguna celda comienza con `=`, `+`, `-` o `@`; no contienen fórmulas ni personas reales.

## Plantillas conocidas

| Tipo | Archivo | Cabecera exacta | Mapeo |
|---|---|---|---|
| Movimiento | [`templates/movimientos.csv`](templates/movimientos.csv) | `id_externo,fecha,monto,moneda,referencia,tipo_movimiento` | Identidad opcional; `DATE`; `NUMERIC(18,2)` positivo; `ARS`; texto opcional; `CREDITO`. |
| Comprobante | [`templates/comprobantes.csv`](templates/comprobantes.csv) | `id_externo,fecha,monto,moneda,referencia,clase` | Identidad opcional; `DATE`; `NUMERIC(18,2)` positivo; `ARS`; texto opcional; `VENTA` o `COBRO`. |

Cabecera, orden y cantidad de columnas son parte de la versión de plantilla. Las filas comienzan en el número 2. Espacios no alteran `datos_originales`; la representación tipada se guarda aparte. Un CSV estructuralmente ilegible produce lote `FALLIDO`; errores de fila producen `INVALIDO` y permiten continuar.

## Resultado esperado

| Fixture | Clasificación | Evidencia/códigos esperados |
|---|---|---|
| [`movimientos-validos.csv`](fixtures/movimientos-validos.csv) | `PROCESADO`; 3 `PENDIENTE` | Tres créditos ARS; referencia vacía permitida. |
| [`comprobantes-validos.csv`](fixtures/comprobantes-validos.csv) | `PROCESADO`; 3 `PENDIENTE` | Tres ventas/cobros ARS. |
| [`movimientos-invalidos.csv`](fixtures/movimientos-invalidos.csv) | `PROCESADO_CON_ERRORES`; 3 `INVALIDO` | `FECHA_INVALIDA`, `MONTO_NO_POSITIVO`, `MONEDA_NO_ADMITIDA` y `TIPO_MOVIMIENTO_NO_ADMITIDO`. |
| [`comprobantes-invalidos.csv`](fixtures/comprobantes-invalidos.csv) | `PROCESADO_CON_ERRORES`; 3 `INVALIDO` | `FECHA_INVALIDA`, `MONTO_NO_POSITIVO`, `MONEDA_NO_ADMITIDA` y `CLASE_NO_ADMITIDA`. |
| [`movimientos-duplicados.csv`](fixtures/movimientos-duplicados.csv) | `PROCESADO_CON_ERRORES`; 2 elegibles, 2 `INVALIDO` | Segunda `MOV-D01`: `ID_EXTERNO_DUPLICADO`; cuarta fila: `HUELLA_FILA_DUPLICADA`. |
| [`comprobantes-duplicados.csv`](fixtures/comprobantes-duplicados.csv) | `PROCESADO_CON_ERRORES`; 2 elegibles, 2 `INVALIDO` | Segunda `COMP-D01`: `ID_EXTERNO_DUPLICADO`; cuarta fila: `HUELLA_FILA_DUPLICADA`. |
| [`movimientos-estructura-invalida.csv`](fixtures/movimientos-estructura-invalida.csv) | `FALLIDO`; sin filas | `CABECERA_INCOMPATIBLE`. |
| [`comprobantes-estructura-invalida.csv`](fixtures/comprobantes-estructura-invalida.csv) | `FALLIDO`; sin filas | `CABECERA_INCOMPATIBLE`. |

## Archivo repetido

La duplicidad de archivo se prueba enviando nuevamente **los mismos bytes** de cualquier fixture, sin editar nombre ni fin de línea durante la prueba. Todo primer intento no `DUPLICADO` reserva la huella: esto incluye un lote `FALLIDO` por estructura y un intento `FALLIDO` con `template_id` desconocido. El segundo intento queda `DUPLICADO`, referencia al primer lote y no crea registros, aunque luego se envíe un `template_id` válido. Los fixtures `*-duplicados.csv` prueban duplicidad de fila, que es un caso diferente.

## Seguridad y normalización

El importador rechaza fórmulas aun cuando el valor aparezca en una columna textual. La huella de archivo usa los bytes exactos. La clave de fila usa versión, fuente, tipo e ID externo original; sin ID usa campos originales estables y encuadrados por longitud. La referencia solo se normaliza para ranking y nunca modifica la celda original.
