# Frontend

Aplicación React 19 + TypeScript + Vite.

## Módulos visibles

- Importar.
- Consolidado.
- Propuestas: Automáticas, Manual y Auditoría.
- Historial.

Pendientes fue eliminado de la navegación; sus casos se cubren desde Consolidado y Manual.

## Desarrollo

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

La API predeterminada es `http://localhost:8000`. Puede cambiarse con `VITE_API_BASE_URL`.

## Verificación

```powershell
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Última validación: 17 pruebas y build aprobados.

## Persistencia

La sesión, filtros, pestañas y selecciones operativas se guardan por usuario en `localStorage`. Los datos financieros y estados de negocio permanecen en la API/PostgreSQL.
