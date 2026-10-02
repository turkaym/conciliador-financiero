# Wireframes de baja fidelidad

Seis SVG textuales describen el recorrido anterior a codificación. No son capturas ni evidencia de una interfaz implementada. Cada archivo incluye `title`, `desc`, labels visibles, foco señalado y estados relevantes.

| Paso | Wireframe | RF y estados |
|---:|---|---|
| 1 | [Login](01-login.svg) | RF-01; vacío, credencial inválida, acceso correcto |
| 2 | [Carga CSV](02-carga-csv.svg) | RF-02, RF-04; selección, validación previa, envío |
| 3 | [Resultado](03-resultado-carga.svg) | RF-03, RF-05, RF-06; procesado, mixto, fallido, duplicado |
| 4 | [Pendientes](04-pendientes.svg) | RF-07; filtros, lista, vacío |
| 5 | [Revisión de propuestas](05-revision-propuestas.svg) | RF-08–RF-11; ranking, explicación, confirmar, rechazar |
| 6 | [Detalle, historial y reversión](06-detalle-historial-reversion.svg) | RF-12, RF-13; activa, revertida, motivo/auditoría |

## Navegación

Después del acceso, la navegación común ofrece **Cargas**, **Pendientes**, **Propuestas** e **Historial**. Carga conduce a resultado; resultado enlaza errores o propuestas generadas automáticamente; una propuesta conduce a conciliación; historial abre detalle. `Tab` recorre controles en orden visual, `Enter` activa, los mensajes se anuncian y el foco vuelve al título tras navegar.

Los estados se distinguen por texto y forma, nunca solo por color. Las confirmaciones destructivas exigen diálogo y motivo cuando corresponde. El MVP solo permite revertir una conciliación activa; un rechazo de propuesta es terminal.
