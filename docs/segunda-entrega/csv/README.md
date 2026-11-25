# CSV y casos de prueba

Todos los archivos contienen datos ficticios.

## Archivos por fuente

En `templates/`:

| Archivo | Tipo/fuente | Uso |
|---|---|---|
| `banco-nacion-movimientos-prueba.csv` | Movimiento / Banco Nación | Esquema bancario genérico. |
| `galicia-movimientos-prueba.csv` | Movimiento / Galicia | Esquema bancario genérico. |
| `mercado-pago-movimientos-prueba.csv` | Movimiento / Mercado Pago | Exportación técnica de Mercado Pago. |
| `mercado-pago-comprobantes-prueba.csv` | Comprobante / Mercado Pago | Genera coincidencias con el archivo de movimientos. |
| `tienda-nube-comprobantes-prueba.csv` | Comprobante / Tienda Nube | Ventas/cobros de prueba. |
| `arca-comprobantes-prueba.csv` | Comprobante / ARCA | Comprobantes de prueba. |

Para demostrar Automáticas, importar los dos archivos de Mercado Pago. El matcher puede mostrar más de una alternativa cuando varios registros cumplen monto y ventana de fecha; confirmar una caduca las incompatibles.

## Esquemas activos

- Bancos tradicionales: `Referencia,Fecha,Crédito,Moneda,Descripción`.
- Mercado Pago movimientos: `SOURCE_ID,DATE,REAL_AMOUNT,CURRENCY_ID,EXTERNAL_REFERENCE,TRANSACTION_TYPE`.
- Mercado Pago comprobantes: `SOURCE_ID,DATE,TRANSACTION_AMOUNT,CURRENCY_ID,EXTERNAL_REFERENCE,TRANSACTION_TYPE`.
- Tienda Nube: número de orden, fecha, total, moneda, medio y estado de pago.
- Facturas físicas OCR-a-CSV: número, fecha, importe, moneda, CAE, CUIT, tipo y punto de venta.
- ARCA: número, fecha, importe total, moneda, autorización, tipo, punto de venta y CUIT.

La fuente Facturas físicas no procesa imágenes: espera el CSV producido por una herramienta OCR externa.

## Fixtures canónicos

`fixtures/` conserva ocho casos:

- Movimientos/comprobantes válidos.
- Movimientos/comprobantes inválidos.
- Duplicados por fila.
- Cabecera incompatible.

## Duplicados

Existen dos niveles:

1. Archivo: mismos bytes de un lote que reserva la huella → lote `DUPLICADO`.
2. Fila: misma identidad dentro del archivo o contra lotes anteriores → fila `INVALIDO`, referencia al original y continuación del resto.

## Formatos

El parser soporta UTF-8 y CP1252, delimitadores coma/punto y coma/tabulación y formatos regionales configurados. Los originales se preservan; las conversiones tipadas no los reemplazan.
