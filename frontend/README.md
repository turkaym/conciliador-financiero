# Frontend de Conciliador

Shell React + Vite + TypeScript para el MVP. La pantalla de acceso consume el contrato aprobado de `POST /api/v1/auth/login` y mantiene una sesión bearer temporal en el almacenamiento local del navegador.

## Desarrollo

```bash
npm install
npm run dev
```

La API se busca por defecto en `http://localhost:8000`. Para cambiarla, defina `VITE_API_BASE_URL` antes de iniciar Vite o ejecutar el build.

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run build
```

## Verificación

```bash
npm test
npm run build
```

La sesión no conserva contraseñas. Las credenciales de demostración se documentan en el README raíz y el backend.

## Límite

- **Entrada:** acciones del usuario y respuestas de `/api/v1`.
- **Salida:** vistas accesibles y comandos explícitos a la API.
- **Dependencia:** los módulos dependen del contrato API, nunca de estructuras de base de datos.
- **Exclusiones:** registro, recuperación de contraseña, roles y workflows posteriores del MVP.

Consulte [`src/modules/`](src/modules/) y los [wireframes](../docs/segunda-entrega/wireframes/README.md).
