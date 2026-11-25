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
