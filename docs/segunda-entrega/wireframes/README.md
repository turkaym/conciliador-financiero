# Wireframes de baja fidelidad

Los SVG son artefactos históricos del diseño previo y no capturas de la interfaz actual.

| Paso original | Wireframe | Correspondencia actual |
|---:|---|---|
| 1 | [Login](01-login.svg) | Acceso vigente. |
| 2 | [Carga CSV](02-carga-csv.svg) | Importar, ahora sin selector de plantilla. |
| 3 | [Resultado](03-resultado-carga.svg) | Resultado y errores del lote. |
| 4 | [Pendientes](04-pendientes.svg) | Reemplazado por Consolidado con `Conciliado: No`. |
| 5 | [Revisión](05-revision-propuestas.svg) | Propuestas > Automáticas y Manual. |
| 6 | [Detalle/reversión](06-detalle-historial-reversion.svg) | Auditoría e Historial. |

## Navegación implementada

Después del acceso: **Importar**, **Consolidado**, **Propuestas** e **Historial**. Propuestas contiene Automáticas, Manual y Auditoría. Los filtros y pestañas se conservan por usuario.

Los wireframes se mantienen como evidencia de evolución del diseño; para validar la experiencia vigente deben utilizarse la aplicación y la [guía funcional](../../conciliador-mvp-guide.md).
