# Conciliación

- Confirma/rechaza propuestas con locks y revalidación.
- Crea pares manuales mediante `POST /reconciliations/manual`.
- Lista conciliaciones activas con filtros de Auditoría.
- Exporta asiento contable CSV Debe/Haber.
- Revierte con motivo, actor y fecha.

Confirmar caduca propuestas generadas que compartan movimiento o comprobante. Revertir una automática genera una propuesta nueva; revertir una manual libera ambos registros. La sincronización posterior puede volver a detectar cualquier pareja automática válida.

Las revertidas permanecen en la base y en el historial, pero no aparecen en la vista activa por defecto.
