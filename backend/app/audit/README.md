# Auditoría

- **Propósito:** agregar eventos atribuibles en la misma transacción que los hechos de dominio.
- **Entrada:** tipo, un objetivo, actor humano, motivo requerido y datos JSON.
- **Salida:** evento cronológico inmutable.
- **RF:** RF-11–RF-13; RNF-03.
- **Dependencias:** repositorio de eventos y contexto transaccional.
- **Exclusiones:** reemplazar entidades, mutar eventos y analítica.
