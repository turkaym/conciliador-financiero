# Propuestas

- Evalúa parejas ARS con monto exacto y ventana de ±3 días.
- Usa `ref-nfkd-v1` para ordenar y explicar referencias.
- Genera propuestas al importar, durante reversión automática y mediante `POST /proposals/sync`.
- `synchronize_for_user` bloquea registros disponibles, recorre sus lotes y evita duplicados `GENERADA` o rechazos idénticos.
- Los históricos `CONFIRMADA`/`CADUCADA` no impiden una evaluación nueva cuando los registros vuelven a estar libres.
- Una propuesta de reversión es una entidad nueva vinculada a la conciliación revertida; nunca se reabre la original.
- `manual-v1` identifica decisiones manuales creadas por el módulo de conciliación.
