# Importación

- **Propósito:** recibir un CSV, calcular la huella de sus bytes y controlar el ciclo del lote.
- **Entrada:** IDs de fuente y plantilla exacta, tipo, nombre y bytes CSV.
- **Salida:** identidad, estado, totales y errores estructurales del lote.
- **RF:** RF-02, RF-03, RF-06; RN-10, RN-11.
- **Dependencias:** catálogos, validación, auditoría y repositorios de lote.
- **Exclusiones:** matching, decisiones humanas, almacenamiento externo y colas asíncronas.

MVP-04 procesa sincrónicamente los bytes CSV almacenados después de reservar un lote. La cabecera se valida antes de persistir filas; los errores de fila se conservan en orden determinista de fila física y campo.
