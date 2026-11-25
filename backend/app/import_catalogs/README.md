# Catálogos de importación

- **Propósito:** exponer fuentes activas y plantillas versionadas compatibles.
- **Entrada:** consulta autenticada y filtros opcionales de fuente/tipo.
- **Salida:** descriptores de fuentes y plantillas.
- **RF:** RF-02.
- **Dependencias:** solo interfaces de lectura de catálogos.
- **Exclusiones:** integraciones, edición de plantillas y mapeo manual.

MVP-03 exposes active sources and versioned templates through authenticated
catalog endpoints. API types are `MOVIMIENTO` and `COMPROBANTE`; database source
types remain the approved `BANCO` and `COMPROBANTES` values.

Cada fuente activa tiene un único esquema CSV activo. La interfaz resuelve ese
esquema al elegir la fuente, sin pedir al usuario que seleccione una plantilla.
Los esquemas bancarios sin especificación pública usan el placeholder común
`Referencia, Fecha, Crédito, Moneda, Descripción`. Mercado Pago y ARCA usan los
nombres técnicos publicados, mientras que Tienda Nube conserva un esquema
extensible hasta validarlo con una exportación real. `Facturas físicas (OCR a
CSV)` representa la salida tabular del proceso OCR; este módulo no procesa
imágenes ni PDF directamente.

La deduplicación se aplica tanto dentro del archivo como contra registros válidos
de lotes anteriores de la misma fuente y tipo. Las filas repetidas se registran
como inválidas con referencia al registro original, se omiten del movimiento o
comprobante canónico y no impiden procesar las demás filas del lote.
