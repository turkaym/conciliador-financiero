# Requerimientos vigentes

## Funcionales

| ID | Requerimiento | Criterio de aceptación |
|---|---|---|
| RF-01 | Autenticar usuarios pre-registrados. | Credenciales válidas entregan JWT; inválidas se rechazan sin revelar existencia. |
| RF-02 | Resolver automáticamente el esquema CSV según tipo y fuente. | La UI no muestra Plantilla y sí las columnas esperadas. |
| RF-03 | Validar estructura y filas sin detener válidas por errores independientes. | El lote distingue procesado, mixto, sin válidos, fallido y duplicado. |
| RF-04 | Detectar duplicados dentro del archivo y contra lotes anteriores. | El duplicado queda inválido, referencia al original y no crea otra transacción. |
| RF-05 | Consultar consolidados de movimientos y comprobantes. | Permite fuente, fecha, conciliado, orden y paginación. |
| RF-06 | Generar coincidencias automáticas explicables. | Exige ARS, monto exacto y ±3 días; se sincroniza al importar, revertir, ingresar o presionar Buscar coincidencias. |
| RF-07 | Confirmar o rechazar propuestas con intervención humana. | Confirmar crea conciliación activa y caduca alternativas incompatibles; rechazar exige motivo. |
| RF-08 | Crear conciliaciones manuales. | Ambos registros pertenecen al usuario, están disponibles y se confirman atómicamente. |
| RF-09 | Auditar y revertir conciliaciones. | Lista activas, filtra, exige motivo al deshacer y libera ambos registros. |
| RF-10 | Regenerar coincidencias después de una reversión. | Una automática produce propuesta nueva; una manual vuelve a candidatos y puede ser redetectada por el sincronizador. |
| RF-11 | Exportar asiento contable CSV. | Dos líneas por conciliación activa filtrada: banco al Debe y comprobante al Haber. |
| RF-12 | Consultar historial. | Eventos conservan objetivo, actor, fecha y motivo aplicable. |
| RF-13 | Persistir estado de navegación por usuario. | Consolidado, Manual y Auditoría recuperan pestañas, filtros y selecciones desde `localStorage`. |

## No funcionales

| ID | Requerimiento | Criterio |
|---|---|---|
| RNF-01 | Atomicidad e integridad. | Confirmación/reversión no dejan cambios parciales y una transacción solo integra una conciliación activa. |
| RNF-02 | Exactitud monetaria. | Montos usan decimal exacto y se serializan como cadenas. |
| RNF-03 | Idempotencia del matcher. | Repetir sincronización no duplica propuestas generadas ni revive rechazos. |
| RNF-04 | Trazabilidad. | Propuestas registran regla, normalizador, huella, origen y explicación. |
| RNF-05 | Seguridad académica. | Secretos fuera del repositorio, hash de contraseñas y datos ficticios. |
| RNF-06 | Aislamiento por usuario. | Consultas y acciones solo alcanzan lotes/registros propios. |
| RNF-07 | Usabilidad ante concurrencia. | Un 409 por propuesta caducada actualiza el listado y comunica el motivo. |
| RNF-08 | Consistencia documental. | README, contrato, reglas y guías describen módulos y rutas vigentes. |
