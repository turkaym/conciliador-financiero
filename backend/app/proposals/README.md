# Propuestas

- **Propósito:** generar y ordenar parejas elegibles tras lotes con válidos o durante reversión.
- **Entrada:** registros habilitados y pendientes opuestos históricos.
- **Salida:** propuestas versionadas con huella, procedencia, componentes y explicación.
- **RF:** RF-08, RF-09; RN-01, RN-03, RN-04, RN-07.
- **Dependencias:** repositorios de pendientes, conciliaciones y propuestas; bloquea registros por ID ascendente.
- **Exclusiones:** generación manual pública, confirmación automática y reapertura de rechazos.
- **MVP-06:** `ref-nfkd-v1` normaliza referencias para explicar y ordenar candidatos; ARS, monto exacto y ventana inclusiva de tres días son los únicos criterios de elegibilidad.
