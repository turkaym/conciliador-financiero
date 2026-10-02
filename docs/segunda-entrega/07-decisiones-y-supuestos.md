# Decisiones y supuestos

## Antecedente académico

La primera entrega fue aprobada sin observaciones. La devolución de la segunda entrega pidió completar activos y corregir consistencia. Este paquete incorpora esas correcciones sin presentar funcionalidades como realizadas. El relevamiento y la codificación no comenzaron.

## Decisiones vigentes

| Tema | Decisión | Motivo o costo aceptado |
|---|---|---|
| Arquitectura | Monolito modular y procesamiento síncrono | Reduce operación para el volumen académico; una transacción grande puede retener locks más tiempo |
| Alcance | Cobranzas ARS y conciliación 1:1 | Mantiene un MVP verificable; egresos, multimoneda y otras cardinalidades quedan fuera |
| Procedencia | `FuenteDatos` con tipo, código, nombre y estado | Evita colisiones sin convertir la fuente en integración externa |
| Originales | JSONB inmutable en registro y normalizados tipados en subtipos | Preserva fidelidad y exige estructuras adicionales para integridad |
| Dinero y tiempo | Decimal exacto, fechas de negocio y eventos UTC | Evita error binario y ambigüedad temporal |
| Estados | Texto restringido, transiciones de dominio y transacción | Facilita evolución frente a ENUM, con controles explícitos |
| Duplicados | Todo primer lote no `DUPLICADO`, aun `FALLIDO`, reserva fuente/tipo/huella | El reenvío siempre apunta al primer intento y no reinterpreta bytes ya recibidos |
| Email | `VARCHAR(254)` e índice único sobre `lower(email)` | Evita SQL inválido y una extensión obligatoria |
| Concurrencia | Generación y conciliación bloquean ambos registros por ID ascendente; triggers rechazan `GENERADA` sobre `ACTIVA` y caducan incompatibles al crear `ACTIVA` | Mayor complejidad a cambio de integridad sin serialización global ni orden circular de locks |
| Historial | Evento transversal append-only | Simplifica cronología y requiere considerar crecimiento futuro |
| Diagramas | Ocho fuentes Mermaid dentro de un único documento | Reduce redundancia y mejora lectura en GitHub sin perder vistas |
| Generación | Automática al finalizar un lote procesado, contra pendientes opuestos históricos | Evita dos caminos públicos y conserva alcance incremental |
| Rechazo | Terminal; no existe reapertura manual | Reduce estados y evita una operación indefinida fuera del MVP |
| Referencia | `ref-nfkd-v1` y desempate determinista | Hace reproducible la explicación sin alterar elegibilidad |
| Selección de plantilla | La carga envía `template_id`; nombre y versión solo se muestran desde catálogo | Evita resolver ambiguamente varias versiones activas con el mismo nombre |

## Supuestos por validar

- Las plantillas conocidas representan los CSV de prueba y pueden versionarse sin edición retroactiva.
- Los datos académicos serán ficticios o anonimizados.
- El relevamiento podrá ajustar necesidades sin ampliar automáticamente el MVP.
- Una futura prueba de hasta 10.000 filas registrará resultados observados, no SLA.

## Riesgos y respuesta propuesta

| Riesgo | Respuesta |
|---|---|
| Divergencia entre plantillas y clave deduplicada | Versionar el algoritmo y usar originales estables |
| Carreras o deadlocks | Restricciones de base y orden determinista de bloqueo |
| Contradicciones documentales | Mantener fuentes canónicas, glosario y matriz |
| Datos incompatibles al evolucionar esquema | Validar antes de restricciones y abortar sin pérdida silenciosa |
