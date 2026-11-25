# Acceso

- **Propósito:** capturar credenciales y establecer un contexto autenticado.
- **Entrada/salida:** email/contraseña → sesión o error genérico.
- **RF:** RF-01.
- **Dependencia:** `POST /api/v1/auth/login`.
- **Exclusiones:** registro, recuperación, roles y persistencia local de credenciales.
