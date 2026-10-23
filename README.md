# CONCILIADOR — Plataforma de Conciliación Financiera y Contable

Propuesta académica para la materia **Proyecto Final** de la **Tecnicatura Universitaria en Programación (UTN)**. La primera entrega, aprobada sin observaciones, queda como antecedente del problema, la estrategia de validación, el alcance y la propuesta técnica inicial.

**Estado vigente:** MVP implementado hasta la preparación local de MVP-11. No existe todavía una URL pública ni servicios Render creados.

## Integrantes y disponibilidad

| Integrante | Usuario de GitHub | Rol principal previsto |
|---|---|---|
| Hugo Tcach | `HugoTcach` | Backend, base de datos e infraestructura local |
| Farid Salomón | `turkaym` | Análisis funcional, frontend, documentación y calidad |

La disponibilidad conjunta es de aproximadamente **10 horas semanales**. Ambos integrantes participarán en el relevamiento, la revisión de cambios, las pruebas y la presentación. Se prevé aprendizaje cruzado para evitar que un área dependa de una sola persona.

## Problema e hipótesis inicial

Se plantea que empresas y estudios contables pueden recibir movimientos bancarios y registros o comprobantes en fuentes separadas. La conciliación exige relacionar esos datos, detectar diferencias y conservar evidencia de las decisiones tomadas.

Como hipótesis inicial, cuando este proceso se realiza con comparaciones manuales y herramientas no conectadas pueden aparecer tareas repetitivas, dificultades para identificar pendientes y poca trazabilidad sobre por qué dos registros fueron asociados o descartados. **Esta hipótesis todavía no fue validada mediante entrevistas ni métricas.**

### Actores y necesidades por validar

| Actor | Participación en el flujo | Necesidad propuesta |
|---|---|---|
| Personal administrativo o contable | Reúne fuentes, compara registros y resuelve diferencias | Reducir comparaciones repetitivas sin perder control sobre la decisión |
| Responsable del proceso | Supervisa el estado y revisa excepciones | Identificar pendientes y reconstruir decisiones |
| Empresa o estudio contable | Define criterios y conserva documentación | Contar con un proceso consistente y trazable |

### Flujo actual supuesto

1. Se obtienen movimientos bancarios y registros o comprobantes desde fuentes separadas.
2. Se revisan formatos y se normalizan datos cuando es necesario.
3. Se comparan monto, fecha y referencias para buscar correspondencias.
4. Se investigan diferencias y se decide qué elementos coinciden.
5. Se registran resultados y quedan pendientes los casos no resueltos.

Este flujo es una representación inicial que se validará y corregirá durante el relevamiento.

### Digitalizar y agregar valor

Digitalizar sería trasladar la comparación a una pantalla sin cambiar el proceso. La propuesta busca agregar valor al asistir la comparación con reglas explicables, destacar excepciones, mantener la revisión humana y registrar la trazabilidad básica. No se presupone que ese valor esté demostrado: se evaluará con los actores y con pruebas del flujo.

### Planteamiento formal

**Pregunta del proyecto:** ¿cómo asistir la conciliación entre movimientos bancarios y registros o comprobantes para reducir la revisión repetitiva y hacer visibles las diferencias, sin reemplazar la decisión humana y conservando trazabilidad básica?

## Estrategia de validación

No hay usuarios consultados, resultados ni mediciones disponibles en esta etapa. Para validar la relevancia se propone:

1. Identificar personas que realicen o supervisen conciliaciones en empresas o estudios contables.
2. Realizar entrevistas semiestructuradas sobre fuentes utilizadas, pasos, excepciones, frecuencia y dificultades del proceso.
3. Observar ejemplos anonimizados o datos ficticios representativos, sin solicitar información financiera sensible.
4. Documentar el flujo real y contrastarlo con la hipótesis y los actores iniciales.
5. Probar un prototipo del flujo con datos de prueba y registrar comprensión, utilidad percibida, errores y ajustes solicitados.
6. Revisar el alcance si el problema no resulta recurrente, relevante o compatible con el tiempo de la materia.

La relevancia se considerará respaldada cuando el relevamiento confirme la necesidad de relacionar fuentes separadas, resolver excepciones y conservar trazabilidad, y cuando el flujo propuesto pueda evaluarse con casos representativos. Las métricas y criterios cuantitativos se definirán después del relevamiento, no antes.

## Propuesta de valor y alternativas existentes

Se propone una herramienta acotada a la conciliación entre dos fuentes, con reglas visibles de coincidencia, revisión humana y trazabilidad de las decisiones.

| Categoría alternativa | Aporte habitual | Diferenciación que se evaluará |
|---|---|---|
| Hojas de cálculo | Flexibilidad y acceso inmediato | Guiar el flujo, mostrar pendientes y registrar decisiones de manera consistente |
| Portales bancarios aislados | Consulta de movimientos de una entidad | Relacionar movimientos con registros externos en un mismo flujo |
| Sistemas contables o ERP generalistas | Cobertura amplia de procesos administrativos | Concentrarse en una experiencia mínima de conciliación explicable y revisable |

La diferenciación es una propuesta a validar y no implica superioridad demostrada frente a esas categorías.

## Alcance priorizado

### MVP esencial

- Carga manual de dos conjuntos de datos de prueba: movimientos bancarios y registros o comprobantes.
- Validación de estructura y campos requeridos.
- Propuestas de coincidencia por monto, fecha y referencia.
- Revisión manual para confirmar o rechazar propuestas.
- Visualización de elementos pendientes.
- Trazabilidad básica del origen de los datos y de las decisiones.

### Nice to have

- Búsqueda aproximada de referencias con `pg_trgm`.
- Importación asincrónica para archivos grandes.
- Dashboard básico.
- Exportación de resultados.
- Despliegue en una plataforma PaaS.

### Fuera de alcance

- Inteligencia artificial y modelos predictivos.
- OCR.
- Integración productiva con AFIP.
- Integraciones bancarias reales.
- Kubernetes y servidores propios.
- Multi-tenancy.
- Monetización o modalidad SaaS.
- Analítica avanzada.

## Propuesta técnica inicial

### Stack previsto para el MVP

| Área | Tecnologías | Criterio de elección |
|---|---|---|
| Frontend | TypeScript, React y Vite | Tipado, ecosistema maduro, documentación abundante y aprendizaje transferible |
| Backend | Python, FastAPI y Pydantic | API acotada, validación explícita y comunidad amplia |
| Persistencia | SQLAlchemy y Alembic | Acceso estructurado y evolución controlada del esquema |
| Base de datos | PostgreSQL | Integridad relacional, transacciones y trazabilidad |
| Colaboración | Git y GitHub | Control de versiones y revisión conjunta |
| Entorno local | Docker Compose | Entorno reproducible sin convertir la infraestructura en el objetivo del proyecto |

La elección considera el problema, la escala académica del MVP, la madurez de las herramientas, el entorno de desarrollo y el costo de aprendizaje. Se prioriza un stack pequeño, estable y respaldado por documentación y comunidades activas. Mantener estas tecnologías durante el proyecto permitirá concentrar el esfuerzo en el problema y evitar costos innecesarios de capacitación, integración y pruebas derivados de un cambio de stack.

### Base relacional frente a NoSQL

Las conciliaciones relacionan movimientos, registros, propuestas, decisiones y estados pendientes. PostgreSQL favorece este caso por su consistencia, integridad referencial y soporte transaccional. Una base NoSQL podría ser apropiada para datos muy variables o patrones de escala diferentes, pero esas necesidades no están justificadas para el MVP. La decisión se revisará si el relevamiento descubre requisitos incompatibles con el modelo relacional.

### Alternativas de despliegue

- **Desarrollo inicial:** ejecución local reproducible mediante Docker Compose.
- **Alternativa posterior:** PaaS, si se necesita publicar una demostración con menor carga operativa.
- **Fuera del alcance inicial:** administración de servidores propios y Kubernetes, porque agregan complejidad que no valida el problema central.

## Plan de trabajo

La secuencia se ajustará al calendario final de la materia y a los hallazgos del relevamiento.

| Secuencia | Etapa | Responsables | Estado factual | Entregable previsto |
|---:|---|---|---|---|
| 1 | Relevamiento y validación | Hugo y Farid | **No iniciado** | Entrevistas, flujo revisado y necesidades priorizadas |
| 2 | Formatos y diseño | Hugo y Farid | **Documentado** | Formatos ficticios, modelo relacional, reglas y wireframes |
| 3 | Prototipo del flujo | Hugo y Farid | **No iniciado** | Recorrido MVP ejecutable con datos de prueba acordados |
| 4 | Verificación del producto | Hugo y Farid | **No iniciada** | Casos funcionales, pruebas técnicas y limitaciones |
| 5 | Presentación | Hugo y Farid | **No iniciada** | Demostración y documentación final |

Cada etapa reservará tiempo para aprendizaje, integración y revisión conjunta. No se incorporará un nice to have mientras falte un criterio de finalización del MVP esencial.

## Viabilidad

| Dimensión | Evaluación inicial | Medida prevista |
|---|---|---|
| Técnica | El flujo puede resolverse con reglas explícitas y tecnologías maduras adecuadas para la escala del MVP | Construir por etapas, usar datos de prueba y validar primero el recorrido mínimo |
| Temporal | La disponibilidad conjunta es de unas 10 horas semanales | Priorizar el MVP, limitar trabajo simultáneo y ajustar estimaciones al calendario final de la materia |
| Operativa | El sistema requiere formatos claros y participación humana para resolver excepciones | Validar el flujo con actores y mantener reglas y estados comprensibles |
| Conocimientos | La formación académica del equipo brinda una base común y el stack seleccionado cuenta con documentación y comunidades amplias | Organizar aprendizaje cruzado, revisiones conjuntas y documentación de decisiones |

La viabilidad se reevaluará al finalizar el relevamiento y cada etapa. Si el tiempo o el aprendizaje requerido superan lo previsto, se reducirá el alcance antes de agregar infraestructura o funciones secundarias.

## Repositorio

Código y documentación del proyecto: [github.com/turkaym/conciliador-financiero](https://github.com/turkaym/conciliador-financiero)

## Documentación

- [Segunda entrega corregida: índice y recorrido de revisión](docs/segunda-entrega/README.md)
- [Contrato API `/api/v1`](docs/segunda-entrega/09-contrato-api.md)
- [Plantillas y fixtures CSV](docs/segunda-entrega/csv/README.md)
- [Wireframes del MVP](docs/segunda-entrega/wireframes/README.md)
- [Esqueleto backend](backend/README.md), [esqueleto frontend](frontend/README.md) y [esquema PostgreSQL](database/README.md)

## Ejecución local

1. Copie `.env.example` como `.env` y defina un `JWT_SECRET_KEY` local.
2. Ejecute `docker compose up --wait` desde la raíz. En un volumen nuevo, Compose ejecuta `database/schema.sql` y `database/seed.sql` una sola vez.
3. Instale el backend con `backend\\.venv\\Scripts\\python.exe -m pip install -e backend[test]`.
4. Inicie la API con `backend\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir backend --reload`.
5. Inicie el frontend con `npm install && npm run dev` desde `frontend/`.

La aplicación local usa `http://localhost:8000` como API y `http://localhost:5173` como origen permitido por defecto. El usuario demo es `demo@conciliador.local` / `Demo1234!`; son credenciales ficticias para desarrollo y no deben reutilizarse en un entorno público.

## Preparación de despliegue en Render

`render.yaml` define un Blueprint con una base PostgreSQL administrada, un web service FastAPI y un static site Vite. El Blueprint genera `JWT_SECRET_KEY` y referencia la conexión PostgreSQL; no contiene secretos.

1. En Render, conecte el repositorio y seleccione el Blueprint `render.yaml`. Esta acción queda pendiente de autorización remota y no fue ejecutada desde este repositorio.
2. En `conciliador-api`, defina `CORS_ORIGINS` con la URL final del static site, por ejemplo `https://<frontend>.onrender.com`.
3. En `conciliador-frontend`, defina `VITE_API_BASE_URL` con la URL final del web service, por ejemplo `https://<api>.onrender.com`.
4. Guarde los cambios y redeploye el frontend después de configurar `VITE_API_BASE_URL`, porque Vite incorpora esa variable durante el build.

El comando de inicio del backend ejecuta `app.initialize_database`: adquiere un bloqueo transaccional, crea el esquema solamente si falta `public.usuario` y ejecuta el seed determinista e idempotente en cada arranque. No ejecuta un reset destructivo. Render inyecta `PORT` y Uvicorn escucha en `0.0.0.0`; `/health` es el health check.

### Credenciales y variables requeridas

- `DATABASE_URL`: la referencia del Blueprint a la base administrada.
- `JWT_SECRET_KEY`: generado por Render; nunca lo agregue al repositorio.
- `CORS_ORIGINS`: URL exacta del frontend público, sin barra final.
- `VITE_API_BASE_URL`: URL exacta de la API pública, sin barra final.
- `DATABASE_SCHEMA_PATH` y `DATABASE_SEED_PATH`: rutas versionadas usadas por el inicializador.

El seed crea o reactiva el usuario demo y los catálogos. Para una demostración pública, cambie las credenciales documentadas o elimine el usuario demo mediante un procedimiento seguro antes de usar datos reales.

### Smoke test posterior al despliegue

Cuando los servicios existan y sus URLs estén disponibles, verifique desde una máquina autorizada:

1. `curl -fsS https://<api>.onrender.com/health` devuelve `{"status":"healthy"}`.
2. El frontend público carga sin errores de assets ni de consola.
3. El login con las credenciales demo configuradas recibe un token.
4. Se cargan los dos CSV de `docs/segunda-entrega/csv/fixtures/`, se inspeccionan errores y pendientes, y se verifica una propuesta.
5. Se confirma una propuesta, se revisa historial, se revierte la conciliación y se confirma que ambos registros vuelven a pendientes.
6. Se repite el arranque o redeploy del backend y se comprueba que el seed no duplica catálogos ni reinicia datos.

MVP-11 queda preparado localmente, pero no se considera completo hasta crear los servicios Render y ejecutar este smoke test remoto con autorización explícita.
