# CONCILIADOR — Plataforma de Conciliación Financiera y Contable

CONCILIADOR es una propuesta académica para centralizar movimientos bancarios, registros y comprobantes, sugerir coincidencias mediante criterios verificables y reservar la intervención humana para las excepciones. La primera entrega, con cierre el **30/08/2026**, documenta el problema, el alcance viable del producto mínimo (MVP), la arquitectura prevista y el plan de trabajo. El repositorio todavía no contiene una implementación validada.

## Problema y contexto

Empresas y estudios contables reciben información dispersa de bancos, pasarelas de pago y comprobantes. Cuando la conciliación se realiza manualmente, aumenta el tiempo dedicado a comparar registros, se favorecen errores operativos y se dificulta reconstruir quién tomó cada decisión y por qué.

La propuesta no parte de métricas ni entrevistas aún validadas. Su viabilidad inicial se apoya en acotar el problema a un flujo observable: importar datos, detectar posibles correspondencias, revisar excepciones y conservar trazabilidad básica.

## Actores involucrados

| Actor | Necesidad principal | Participación esperada |
|---|---|---|
| Personal administrativo y contable | Reducir la revisión repetitiva y localizar diferencias | Importar información, revisar propuestas y resolver pendientes |
| Responsables de empresas o estudios contables | Conocer el estado de la conciliación y rastrear decisiones | Consultar pendientes y trazabilidad |
| Equipo del proyecto | Construir y validar una solución académica viable | Analizar, implementar, probar, documentar y presentar |

## Propuesta de valor

Centralizar las fuentes que intervienen en la conciliación, proponer coincidencias por reglas explícitas y concentrar el trabajo humano en los casos ambiguos o incompletos. La decisión final permanece bajo control del usuario y cada confirmación o corrección debe dejar una referencia trazable.

## Objetivos

### Objetivo general

Diseñar e implementar un MVP que asista la conciliación entre movimientos financieros y registros contables mediante importación, propuestas de coincidencia, revisión manual y trazabilidad básica.

### Objetivos específicos

- Importar movimientos bancarios y registros o comprobantes mediante formatos definidos y validables.
- Identificar posibles coincidencias aplicando monto, fecha y referencia como criterios explícitos.
- Permitir que una persona confirme, rechace o corrija una propuesta de conciliación.
- Presentar los movimientos y registros pendientes de resolución.
- Registrar el origen de los datos y las decisiones realizadas durante la conciliación.
- Verificar el flujo principal con pruebas de backend y controles de calidad del frontend formalizados durante el desarrollo.

## Alcance del MVP

### Incluido

- Importación de movimientos bancarios.
- Importación de registros o comprobantes.
- Validación básica de los datos recibidos.
- Propuestas de coincidencia por monto, fecha y referencia.
- Confirmación y corrección manual de coincidencias.
- Vista de elementos pendientes.
- Trazabilidad básica de importaciones y decisiones.

### Fuera del alcance inicial

- Inteligencia artificial y modelos predictivos.
- Reconocimiento óptico de caracteres (OCR).
- Despliegue con Kubernetes.
- Monetización o modalidad SaaS.
- Analítica avanzada.
- Integración productiva con AFIP.

Estos puntos representan posibles líneas de evolución. No son capacidades comprometidas ni garantizadas para el MVP.

## Flujo principal

1. El usuario importa movimientos bancarios y registros o comprobantes.
2. El sistema valida la estructura y conserva el origen de cada dato aceptado.
3. El sistema compara los registros y propone coincidencias por monto, fecha y referencia.
4. El usuario revisa cada propuesta y la confirma, rechaza o corrige.
5. El sistema actualiza los pendientes y registra la decisión para su consulta posterior.

## Stack tecnológico

| Área | Tecnologías previstas | Propósito y justificación |
|---|---|---|
| Frontend | TypeScript, React 19, Vite | SPA tipada, componentes de interfaz y ciclo de desarrollo ágil |
| Estado y comunicación | Zustand, Axios | Estado cliente acotado y comunicación explícita con la API |
| Estilos | Tailwind CSS | Construcción consistente y rápida de la interfaz |
| Backend | Python 3.11, FastAPI, Pydantic 2 | Productividad del equipo, API tipada y validación de entradas y salidas |
| Persistencia | SQLAlchemy 2, Alembic | Acceso estructurado a datos y evolución controlada del esquema |
| Datos | PostgreSQL 16, `pg_trgm` | Integridad transaccional y apoyo a búsquedas aproximadas sobre referencias |
| Procesamiento asíncrono | Celery, RabbitMQ, Redis | Ejecución desacoplada de importaciones o tareas que no deben bloquear solicitudes |
| Archivos | MinIO / S3 | Almacenamiento de archivos importados mediante una interfaz compatible con objetos |
| Infraestructura | Docker Compose, Traefik, PgBouncer | Entorno reproducible, enrutamiento y administración de conexiones |
| Calidad | pytest, FastAPI TestClient, lint y build de frontend | Verificación automatizable del backend y controles estáticos y de compilación del frontend; su configuración aún debe formalizarse |

El stack prioriza integridad transaccional, tipado, productividad, procesamiento asíncrono y reproducibilidad. Su amplitud también introduce complejidad operativa; cada componente de apoyo deberá incorporarse solo cuando el flujo del MVP lo justifique.

## Arquitectura resumida

La arquitectura prevista es un **monolito modular con una SPA y workers distribuidos**, no un conjunto de microservicios.

```text
SPA React
    |
    v
API FastAPI (módulos funcionales)
    |-------------------|
    v                   v
PostgreSQL          Cola de tareas ---> Workers Celery
                        |                    |
                        |--------------------v
                                      MinIO / S3
```

- La SPA concentra la interacción del usuario y consume una API HTTP.
- El backend organiza las capacidades por módulos dentro de una única aplicación desplegable.
- PostgreSQL protege la consistencia de importaciones, conciliaciones y trazabilidad.
- La cola y los workers aíslan tareas potencialmente costosas sin convertir el sistema en microservicios.
- Docker Compose busca reproducir el entorno local; Traefik y PgBouncer apoyan el acceso y las conexiones cuando su incorporación sea necesaria.

## Plan de trabajo

| Etapa | Entregable | Responsables | Criterio de finalización | Estado |
|---|---|---|---|---|
| Definición académica | Propuesta, alcance, stack, arquitectura y plan documentados | Ambos integrantes | README revisado y alineado con la primera entrega, cuyo cierre es el 30/08/2026 | En elaboración |
| Saneamiento técnico | Inventario y evaluación reproducible del prototipo separado | Hugo Tcach y Farid Salomón | Componentes candidatos identificados, dependencias revisadas y exclusiones documentadas, sin trasladar material no verificado | Pendiente |
| Base del proyecto | Estructura del monolito modular, SPA y entorno local mínimo | Hugo Tcach con revisión de Farid Salomón | Aplicaciones iniciables en un entorno reproducible y configuración sin secretos | Pendiente |
| Importación | Flujo de carga y validación de movimientos y registros | Hugo Tcach en backend; Farid Salomón en interfaz y criterios funcionales | Datos válidos aceptados, errores informados y origen registrado | Pendiente |
| Conciliación | Reglas de coincidencia, revisión manual y pendientes | Ambos integrantes | Flujo principal ejecutable con confirmación, rechazo o corrección y trazabilidad básica | Pendiente |
| Verificación | Pruebas de backend y controles de lint y build de frontend formalizados | Farid Salomón con apoyo de Hugo Tcach | Comandos de verificación documentados y ejecutados sobre el alcance implementado | Pendiente |
| Presentación | Demostración y documentación del alcance alcanzado | Ambos integrantes | Flujo verificable presentado y limitaciones pendientes declaradas | Pendiente |

## Distribución de roles

| Integrante | Rol principal | Responsabilidades |
|---|---|---|
| Hugo Tcach (`HugoTcach`) | Liderazgo técnico | Backend, base de datos e infraestructura |
| Farid Salomón (`turkaym`) | Análisis funcional | Frontend, documentación y aseguramiento de calidad |

Ambos integrantes participan también en la planificación, revisión de cambios, pruebas y presentación del proyecto.

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación prevista |
|---|---|---|
| Alcance excesivo para un proyecto académico | Dispersión y entregas incompletas | Priorizar el flujo principal y mantener la evolución potencial fuera del MVP |
| Prototipo separado sin saneamiento ni verificación | Incorporación de defectos, dependencias o supuestos desconocidos | Evaluar por componentes y trasladar únicamente material revisado y reproducible |
| Variabilidad de formatos de entrada | Importaciones ambiguas o inválidas | Definir formatos admitidos, validar campos y reportar rechazos con claridad |
| Coincidencias incorrectas o ambiguas | Decisiones contables equivocadas | Usar reglas explícitas, presentar la evidencia y exigir intervención humana ante excepciones |
| Complejidad operativa del stack | Mayor costo de configuración y diagnóstico | Incorporar servicios de apoyo de forma incremental y documentar su necesidad |
| Pruebas aún no formalizadas | Regresiones difíciles de detectar | Establecer comandos reproducibles y casos del flujo principal antes de considerar una etapa finalizada |
| Manejo de información financiera | Exposición o pérdida de datos | Evitar secretos en el repositorio, limitar datos de prueba y revisar controles de acceso antes de usar información real |

## Criterios de éxito verificables

- El sistema puede importar un conjunto válido de movimientos y otro de registros o comprobantes, conservando su origen.
- Los datos inválidos se rechazan o señalan sin incorporarse silenciosamente.
- Cada propuesta muestra los criterios que motivaron la posible coincidencia.
- El usuario puede confirmar, rechazar o corregir una propuesta.
- Los elementos sin resolución permanecen visibles como pendientes.
- Las decisiones manuales dejan trazabilidad básica consultable.
- El flujo principal cuenta con verificaciones reproducibles de backend y controles de lint y build de frontend.
- Las capacidades fuera del MVP no se presentan como implementadas.

## Estado actual

Este repositorio inicia como base académica y, por el momento, contiene únicamente esta documentación. Existe un prototipo avanzado en un entorno separado, pero debe sanearse, revisar sus dependencias y verificarse antes de incorporar cualquier parte. En consecuencia, no se afirma que las funcionalidades descritas estén terminadas o probadas.

## Repositorio

Código y documentación del proyecto: [github.com/turkaym/conciliador-financiero](https://github.com/turkaym/conciliador-financiero)
