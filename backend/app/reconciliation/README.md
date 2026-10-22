# Conciliación

- **Propósito:** confirmar/rechazar propuestas y revertir conciliaciones atómicamente con recomparación.
- **Entrada:** ID, actor autenticado y motivo requerido.
- **Salida:** decisión terminal o conciliación activa/revertida, propuestas nuevas y auditoría.
- **RF:** RF-10–RF-12; RN-02, RN-05–RN-09, RN-12.
- **Dependencias:** repositorios de propuestas, conciliaciones, registros y auditoría; comparte locks ascendentes.
- **Exclusiones:** confirmación automática, borrado de historia y reapertura manual.
- **MVP-07:** `POST /api/v1/proposals/{id}/confirm` y `/reject` son transiciones terminales autenticadas; `GET /api/v1/reconciliations/{id}` y `GET /api/v1/history` exponen detalle e historial con alcance por propietario.
