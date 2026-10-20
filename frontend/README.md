# Esqueleto documental del frontend

Este directorio documenta los límites funcionales de la UI prevista. No contiene código React, manifiestos, dependencias, resultados de build ni imagen de contenedor.

## Límite

- **Entrada:** acciones del usuario y respuestas de `/api/v1`.
- **Salida:** vistas accesibles y comandos explícitos a la API.
- **Dependencia:** los módulos dependen del contrato API, nunca de estructuras de base de datos.
- **Exclusiones:** arranque de aplicación, biblioteca de estado, sistema de estilos y pruebas ejecutables.

Consulte [`src/modules/`](src/modules/) y los [wireframes](../docs/segunda-entrega/wireframes/README.md).
