# Propuestas

- **Propósito:** generar y ordenar parejas elegibles tras lotes con válidos o durante reversión.
- **Entrada:** registros habilitados y pendientes opuestos históricos.
- **Salida:** propuestas versionadas con huella, procedencia, componentes y explicación.
- **RF:** RF-08, RF-09; RN-01, RN-03, RN-04, RN-07.
- **Dependencias:** repositorios de pendientes, conciliaciones y propuestas; bloquea registros por ID ascendente.
- **Exclusiones:** confirmación automática sin intervención humana y reapertura de rechazos.
- **MVP-07:** las decisiones se delegan al módulo de conciliación; una confirmación crea la conciliación activa y un rechazo conserva el motivo y devuelve los extremos a pendientes cuando no tienen otra propuesta vigente.
- **MVP-06:** `ref-nfkd-v1` normaliza referencias para explicar y ordenar candidatos; ARS, monto exacto y ventana inclusiva de tres días son los únicos criterios de elegibilidad.
- **MVP-08:** la reversión reutiliza el matching determinista con origen `REVERSION`, omite la pareja/evaluación ya confirmada y evita duplicar cualquier evaluación existente.
- **Flujo manual:** `POST /reconciliations/manual` crea una propuesta `manual-v1` y la confirma atómicamente después de bloquear y validar que ambos registros pertenezcan al usuario y sigan pendientes.
- **Búsqueda manual:** `GET /records` permite acotar candidatos no conciliados por banco/entidad, fechas, monto con tolerancia, referencia y lote.
- **Auditoría:** `GET /reconciliations` devuelve cada conciliación con movimiento y comprobante completos; las activas pueden deshacerse mediante el flujo de reversión existente.
