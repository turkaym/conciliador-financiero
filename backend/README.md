# Esqueleto documental del backend

Este directorio define el backend modular previsto; no contiene código de aplicación, manifiestos, dependencias ni imagen de contenedor.

## Límite

- **Entrada:** solicitudes HTTP y bytes CSV desde el futuro adaptador API.
- **Salida:** respuestas tipadas y eventos de dominio persistidos por adaptadores futuros.
- **Dirección:** API/aplicación → dominio ← adaptadores de persistencia.
- **Exclusiones:** configuración de framework, modelos ORM, migraciones, credenciales, jobs y servicios ejecutables.

Consulte [`app/`](app/README.md) para los contratos. Los módulos coordinan mediante contratos explícitos y nunca escriben directamente las tablas de otro módulo.
