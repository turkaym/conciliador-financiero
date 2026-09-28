# Decisiones y supuestos

## Antecedente académico

La primera entrega fue aprobada sin observaciones. Esta segunda entrega amplía su definición antes de codificar; no atribuye devoluciones inexistentes ni presenta funcionalidades como realizadas.

## Decisiones vigentes

| Tema | Decisión | Motivo o costo aceptado |
|---|---|---|
| Arquitectura | Monolito modular y procesamiento síncrono | Reduce operación para el volumen académico; una transacción grande puede retener locks más tiempo |
| Alcance | Cobranzas ARS y conciliación 1:1 | Mantiene un MVP verificable; egresos, multimoneda y otras cardinalidades quedan fuera |
| Procedencia | `FuenteDatos` con tipo, código, nombre y estado | Evita colisiones sin convertir la fuente en integración externa |
| Originales | JSONB inmutable en registro y normalizados tipados en subtipos | Preserva fidelidad y exige estructuras adicionales para integridad |
| Dinero y tiempo | Decimal exacto, fechas de negocio y eventos UTC | Evita error binario y ambigüedad temporal |
| Estados | Texto restringido, transiciones de dominio y transacción | Facilita evolución frente a ENUM, con controles explícitos |
| Duplicados | Identidad contextual e índices únicos parciales | Conserva intentos inválidos y resuelve carreras |
| Email | `VARCHAR(254)` e índice único sobre `lower(email)` | Evita SQL inválido y una extensión obligatoria |
| Concurrencia | `ON CONFLICT`, bloqueos ordenados e índices parciales | Mayor complejidad a cambio de integridad sin serialización global |
| Historial | Evento transversal append-only | Simplifica cronología y requiere considerar crecimiento futuro |
| Diagramas | Ocho fuentes Mermaid dentro de un único documento | Reduce redundancia y mejora lectura en GitHub sin perder vistas |

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
