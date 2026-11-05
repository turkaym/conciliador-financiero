🗺️ Roadmap v14.6: "Saneamiento Distribuido, Seguridad Perimetral & Ignición Frontend"
✅ FASES COMPLETADAS (Cimientos, Motores e Infraestructura)
Fase 1: Core Operativo y Multi-Tenancy
Aislamiento de Datos Estricto: Separación lógica absoluta por esquemas en PostgreSQL administrada mediante inyección dinámica del search_path.

Gestión de Ciclo de Vida: Implementación de la clase TenantManager integrando políticas de Soft-Deletes para preservar el historial inmutable en la base de datos maestra.

Aprovisionamiento Asíncrono: Delegación de la creación de esquemas físicos y generación de DDL iniciales a workers de Celery, erradicando los bloqueos I/O en el hilo principal de la API HTTP.

Orquestación DDL Paralela: Despliegue de esquemas concurrentes (parallel_upgrade.py) aislando transacciones de Alembic en subprocesos nativos del sistema operativo, permitiendo provisionamientos globales sin downtime.

Saneamiento de Fugas Multi-Tenant (Connection Leaks): Reemplazo de generadores clásicos en Celery por Context Managers puros (tenant_session_ctx), garantizando el cierre atómico y matemático de conexiones para evitar la asfixia del pool de PgBouncer.

Aislamiento Híbrido de Transacciones DDL (Anti-Phantom): Inyección de conexiones vivas de SQLAlchemy hacia la API Programática de Alembic. Forzado estructural de la instrucción connection.commit() al finalizar migraciones para asegurar la persistencia en disco previo al sembrado de datos (Data Seeding).

Enrutamiento Asíncrono Centralizado: Mapeo estricto topológico (task_routes) en la configuración de Celery, previniendo la pérdida de eventos en colas huérfanas o no monitoreadas por los agentes.

Fase 2: Administración y Cerrojo Contable
Administración Centralizada: Consolidación unificada de registros mediante la tabla SystemLog.

Escudo Anti-Suicidio: Protección lógica transaccional (is_system = True) implementada sobre las cuentas estructurales base del Plan de Cuentas Argentino.

Estandarización de Timezones: Obligatoriedad de operatoria exclusiva en UTC puro a nivel de motor relacional y variables de entorno.

Bloqueo de Períodos Contables: Interceptores que devuelven rechazos estructurados (HTTP 400) ante intentos de escritura en períodos financieros ya liquidados.

Inmutabilidad Contable Estricta: Implementación de eventos nativos a nivel SQLAlchemy (ORM) que interceptan, bloquean y destruyen cualquier intento de borrado físico (DELETE) en el núcleo financiero, lanzando AccountingImmutabilityError.

Revocación Diferida de Permisos (Denylist JWT): Arquitectura de validación O(1) inyectada en Redis. Invalida tokens comprometidos y destruye cachés de sesiones en tiempo real ante eventos de cierre de sesión (/logout) o suspensión de inquilinos.

Fase 3.1: Arquitectura Frontend por Features y Seguridad
Estado Global: Implementación de Zustand con tipado estricto en React.

Intercepción Perimetral: Despliegue de Proxy Reverso en Vite e inyección de interceptores en Axios para el manejo automatizado de credenciales, cabeceras y refresh tokens.

Fase 3.2: Gestión de Cuentas Bancarias y Movimientos
Pantalla de Listado y Creación: Interfaz de usuario para la gestión de cuentas.

Lógica Visual: Renderizado asíncrono de saldos transaccionales en tiempo real.

Patrón DTO Estricto: Mapeo bidireccional y seguro entre la base de datos (SQLAlchemy) y las interfaces de contrato (Pydantic).

Prevención de N+1 Queries: Uso extensivo y obligatorio de Eager Loading (joinedload, selectinload) en consultas relacionales complejas del ORM.

Fase 3.3: Componente de Ingesta Masiva (Alta Disponibilidad)
Delegación Asíncrona (Celery): Desacoplamiento del procesamiento bloqueante en el parseo de estructuras pesadas (Excel/CSV).

Optimización de Almacenamiento (S3): Implementación de la destrucción automatizada de objetos crudos en el clúster MinIO tras la ingesta exitosa, previniendo el colapso de volúmenes a largo plazo.

Tolerancia a SIGKILL: Refactorización I/O en Celery utilizando manejadores de contexto del sistema operativo (tempfile.mkstemp y os.remove) para evitar la orfandad de archivos locales en /tmp ante reinicios abruptos de contenedores.

Fase 3.4: Integridad de Datos UI y Paginación
Paginación Estricta: Aplicación obligatoria de directivas limit y offset en la totalidad de los endpoints listables.

Conteo en Motor de BD: Cálculos de total_count y validadores booleanos has_more delegados exclusivamente a funciones ventana nativas de PostgreSQL.

Fase 3.5: Blindaje de Enrutamiento y Seguridad de Dominio
Topología de Rutas Segregada: División arquitectónica entre endpoints Públicos (/v1/auth), de Operador y de Administración (/v1/admin), mediada por inyección de dependencias (RoleChecker).

Mapeo Estricto: Uso imperativo de SQLEnum erradicando "magic strings" a nivel de esquema en la base de datos.

Escudo DoS Perimetral Avanzado: Rate Limiter inyectado en el API Gateway operando sobre pipelines de Redis. Evalúa el tráfico paralelamente por IP y por Tenant, e integra validación estricta de cabeceras WAF (CF-Connecting-IP / X-Forwarded-For) mitigando ataques de IP Spoofing.

Sanitización de Orígenes CORS: Inmunidad desarrollada contra inyecciones de espacios en blanco (strip()) en la carga dinámica de orígenes permitidos, previniendo bloqueos 403 accidentales en despliegues de producción.

Fase 3.6: Dashboard de Conciliación y Resiliencia en Tiempo Real
Persistencia de Estado de UI: Almacenamiento local aislado (LocalStorage).

Cerrojo Transaccional API (Anti-Deadlocks): Bloqueos a nivel aplicación previniendo colisiones I/O simultáneas sobre el mismo recurso financiero.

Polling Visual Resiliente: Sincronización UI/Worker mediante sondeo pasivo.

Orquestación Map-Reduce (Zombie Sweeper): Desmantelamiento del cron monolítico. Celery Beat orquesta delegando tareas individuales y asíncronas de limpieza (sweep_tenant_zombies) por cada inquilino, asegurando paralelismo masivo y protección del pool de base de datos.

Colapso del Hilo Principal (Virtualización DOM): Implementación de motor matemático (@tanstack/react-virtual) en la UI para reciclar nodos HTML en memoria ante listas de miles de transacciones.

Resiliencia de Arranque (Fail-Fast & Backoff): Patrón Exponential Backoff en el ciclo de vida (lifespan) de FastAPI tolerando latencias DNS. Verifica conectividad a Redis y aplica Health Checks pasivos (SELECT 1) en PostgreSQL previo a habilitar la escucha de tráfico.

Fase 4: Motor de Ingesta, Normalización y Activación
Parser Universal (CSV/Excel): Motor de ingesta unificado y agnóstico al formato de origen.

Barrera Anti-Duplicados: Hashing criptográfico con intercepción de colisiones IntegrityError (devolviendo HTTP 409).

Motor OTP Asíncrono (Activación): Generación de "One Time Passwords" criptográficamente seguros (SystemRandom) alojados exclusivamente en Redis (TTL 15 min), sin ensuciar la base de datos relacional.

Destrucción Atómica y Cooldown (Anti-Flooding): Transacciones atómicas en Redis (Pipeline) destruyen el OTP tras validarlo y establecen un candado de espera (Cooldown) de 60 segundos por correo para mitigar ataques masivos de Botnets.

B2B Onboarding Estricto: Contratos DTO (Pydantic) que aplican validación de políticas de contraseña complejas (Regex) y validación de longitud para variables comerciales de inquilinos (CUIT).

Defensa Anti-Enumeración: Endpoints de recuperación estandarizados para devolver respuestas idénticas (HTTP 202) independientemente de la existencia del usuario, dejando ciegos a los atacantes.

Transacciones Compensatorias: Controladores de negocio preparados con sentencias rollback para efectuar depuraciones físicas (Hard Delete) de esquemas incompletos ante fallos en cadena del alta de empresas.

Rotación Segura de JWT (Ventana Deslizante): Renuevo silencioso de tokens a través del endpoint /refresh, emitiendo nuevas credenciales mientras se inserta instantáneamente el token saliente en el Denylist.

Aduana de Normalización: Middleware estricto para estandarizar denominaciones y divisas previo a la inserción en base de datos.

🚧 FOCO ACTUAL: Fase 5 - Motor Fiscal (AFIP/ARCA) Bidireccional y Localización
Desacoplamiento I/O de Base de Datos: Arquitectura obligatoria del IngestManager operando sobre transacciones de base de datos ultra-cortas, estrictamente aisladas de las latencias de red externas en las llamadas a los servidores AFIP para prevenir Pool Exhaustion.

Ingesta Incremental: Descarga automatizada de comprobantes emitidos y recibidos desde portales AFIP (Gap Ingest).

Localización Fiscal Nativa: Cálculo automatizado y estructurado de percepciones y retenciones impositivas (IIBB, Ganancias, IVA).

Aduana Pydantic Fiscal: Capa de validación, sanitización (cast de formatos de fecha YYYYMMDD) y tipado coercitivo de los diccionarios crudos devueltos por la AFIP antes de interactuar con el ORM.

Motor de Ajuste por Inflación: Módulo contable inicial para generación automática de asientos de RECPAM.

🔜 FASES PRÓXIMAS (Escalabilidad, Operaciones y Enterprise Features)
Fase 6: Conciliación y Motor Contable (Arquitectura Enterprise)
Arquitectura N:M Real: Soporte nativo y relacional para Pagos Parciales y cobros agrupados complejos.

Motor de Búsqueda Difusa: Búsquedas inexactas de transacciones delegadas a la base de datos (PostgreSQL pg_trgm). Inyección global del esquema public en el search_path del inquilino, aislando la visibilidad de los índices compartidos.

Paginación Keyset por Lotes: Procesamiento masivo asíncrono utilizando variables de entorno de calibración (BATCH_SIZE).

Erradicación de Deadlocks Relacionales: Inyección estricta de dependencias y ordenamiento matemático de bloqueos en tablas interrelacionadas.

Dead Letter Queue (DLQ): Almacenamiento de tareas fallidas irrecuperables en la base Master para auditoría, envolviendo fallos nativos en RuntimeError para asegurar serialización limpia y delegación en Celery.

Fase 7: Trazabilidad y Seguridad Estructural
Trazabilidad Criptográfica (Audit Trail): Registro forzoso en la base de datos Master de eventos sensibles de alteración de configuración o llaves KMS, indicando usuario, marca de tiempo e IP origen. Todo cambio estructural debe dejar una huella inmutable interceptada automáticamente mediante eventos (after_insert, after_update, after_delete) a nivel de Mapper.

RBAC Estricto y Auditoría: Permisos granulares y flujos de aprobación administrativos.

Prevención de Dependencias Circulares DDL: Aplicación de Lazy Imports dentro de los escuchadores de eventos ORM para evitar colapsos al instanciar los metadatos de Alembic durante el arranque del worker.

Fase 8: Operatoria Comercial, Inventario y Contabilidad Dimensional
Contabilidad Dimensional: Manejo de Centros de Costo, Proyectos y Unidades de Negocio independientes bajo una misma Razón Social.

Red de Puntos de Venta (POS): Arquitectura Multi-Sucursal para retail físico, emitiendo sub-facturaciones.

Analítica Segmentada: Generación de P&L (Estado de Resultados) filtrable dimensionalmente y de forma comparativa por POS.

Fase 9: Automatización Extrema y Motor de Reglas
IA Predictiva: Lectura e ingesta de comprobantes escaneados (OCR) y categorización automatizada de gastos mediante Machine Learning.

Creador de Workflows de Usuario: Motor gráfico para habilitar la construcción de reglas de negocio "If-This-Then-That" a nivel ERP por parte del usuario final.

Fase 10: Super Admin, QA Enterprise y DevOps
Escala Global (K8s): Migración estructurada de Docker Compose a orquestación con Kubernetes (K8s) para alta disponibilidad real (Multi-Node).

Pipeline de QA Automation (BDD/Gherkin): Suite de pruebas End-to-End integradas en el pipeline CI/CD previniendo regresiones arquitectónicas.

📄 Documentación Técnica y Funcional Extendida
Sistema ERP SaaS: "Conciliador" | Versión de Arquitectura: 14.6 Enterprise
1. Arquitectura Base y Ecosistema de Infraestructura
El sistema está construido bajo una topología de microservicios transaccionales orientada a la alta disponibilidad, la resiliencia en bloqueos y el aislamiento absoluto de datos.

Backend (API Gateway & Core): Desarrollado en FastAPI (Python 3.11+). Implementa escudos de Rate Limiting perimetrales y por Tenant en Redis (Pipelines atómicos) con validación anti-spoofing (CF-Connecting-IP). Ciclo de vida gestionado con reintentos exponenciales para tolerancia a fallos de red interna durante la secuencia de arranque.

Base de Datos Relacional: PostgreSQL 16. Aislamiento Multi-Tenant real inyectando search_path. Integración de índices B-Tree parciales para erradicar Full Table Scans en tablas voluminosas.

Multiplexación de Conexiones (PgBouncer): Gestor intermedio de red configurado en modo transaction. Conexiones a BD desde el código Python gestionadas obligatoriamente mediante la clase NullPool para evitar secuestro de sockets y Connection Leaks.

Gestor de Tareas Asíncronas (Workers): Celery orquestado por RabbitMQ. Manejo de fallos críticos capturados y reportados vía RuntimeError para proteger la estabilidad del Daemon principal. Patrón de Orquestación Map-Reduce implementado en rutinas crónicas (ej. Zombie Sweeper).

Almacenamiento de Objetos: MinIO (S3-Compatible) efímero.

Frontend SPA: React 18 (Vite) con arquitectura Feature-Sliced Design (FSD).

2. Normativas de Código y Patrones de Diseño (Reglas Duras)
[REGLA DE ORO 1] Restricción Absoluta de I/O dentro de Transacciones de Base de Datos: Queda determinantemente prohibido ejecutar peticiones HTTP (AFIP, Bancos, APIs de Terceros) manteniendo una sesión de base de datos (Session) abierta. Los conectores I/O deben operar en memoria y abrir la transacción de base de datos exclusivamente durante la fase de persistencia (Guardado). El incumplimiento causa el colapso garantizado por Connection Pool Exhaustion.

[REGLA DE ORO 2] Bypass DDL Dinámico en Migraciones: Operaciones estructurales (DDL) de Alembic deben usar DB_HOST_DIRECT (puerto 5432 nativo), evadiendo el multiplexor PgBouncer (puerto 6432) ya que este no admite operaciones DDL complejas en modo transaccional.

Erradicación de Tablas Fantasma (Phantom DDL): Las operaciones de Alembic por API Programática exigen la ejecución posterior forzada de connection.commit() antes de liberar el hilo, de lo contrario, SQLAlchemy revertirá las migraciones en sistemas sin autocommit.

Cero Generadores en Procesamiento Celery: Funciones ejecutadas por el worker deben invocar el encapsulamiento a través del Context Manager tenant_session_ctx(tenant_id) utilizando el bloque with. El uso de yield o next() en obtención de dependencias asíncronas causará fugas de conexión irreversibles.

Seguridad Atómica en Redis: Transacciones multi-llave en caché (Ej. OTP TTL + Bloqueo de Cooldown) deben estar encapsuladas en redis_client.pipeline(transaction=True) para asegurar que ninguna caída de red deje el motor de seguridad en un estado inconsistente.

Responsabilidad Limitada de los Controladores: Los controladores de FastAPI no validan entropía, no validan regex de CUITs y no determinan longitudes; toda validación estructurada pre-inserción corresponde a los validadores delegados @field_validator de la clase Pydantic.

Estado Global Predecible (Cero Mutación de Contexto Operativo): Queda prohibido el uso de os.chdir() o manipulaciones de los directorios de trabajo del sistema operativo (cwd) en entornos multi-hilo o workers asíncronos. Todas las lecturas e importaciones dinámicas se hacen por resolución de rutas absolutas.

Decoupling de Lógica de Negocio y Respuestas HTTP: Cualquier violación de las reglas de negocio detectadas por la capa de Servicios lanzará ValueError. La API Gateway debe capturarlos y transformar la salida en un limpio HTTP 400 (Bad Request), evitando enviar códigos HTTP 500 (Internal Server Error) por errores atribuibles al usuario final.

PARADIGMA DEL DE TRABAJO:

Cuando realizamos un evolutivo o fix debemos pensarlo como una solución arquitectónica que implique todo el proyecto y analizar esa solución junto con las implicancias que puede tener en otros archivos o partes del código. La solución debe ser profesional, minimalista y con visión 360 del proyecto.
Al terminar un hito o modulo de desarrollo del proyecto en curso deberás: 1. Realizar las pruebas necesarias para asegurarnos de que funciona. 2. Analizar riesgos, cabos sueltos, parches a eliminar o inconsistencias a solucionar. 3. Solicitarme el ROADMAP para actualizarlo, así como la Documentación técnica para agregar o modificar según lo realizado.
Las soluciones y evolutivos deben ser de caracter enterprise, sin parches, con una vision 360 del negocio, sin dejar deuda tecnica, sin inconsistencias, con codigo minimalista, analizando paso a paso cada contendido de codigo interpelado en el proceso y verificando posibles mejoras y buenas prácticas que permitan aprovechar la situacion para aplicarlas.
Al terminar un hito o una fase de desarrollo en éxito debo verificar posibles errores, inconsistencias, cosas que fueron parchadas y deben profesionalizarse o malas practicas, grises o código basura que pueda haber quedado y deba resolverse y diseñar un plan de depuración.
Paso 1- Al tener que realizar una accion que requiere de varios pasos, imprimiras de a un paso por vez, esperando mi OK para ir al paso siguiente. Paso 2- Al corregir un defecto siempre solicitarás la version actual del bloque de código o función implicada, y basándote en esa información proporcionada por mi imprimirás en el paso siguiente la versión corregida. Caso de que conste de varias partes lo haras siguiendo los criterios del paso 1. Paso 3- Al corregir un error jamas emitiras un diagnostico ni pasos de resolucion hasta no haber seguido el paso 2.
Tenes prohibido analizar siempre todo desde una perspectiva positiva. Debes ser honesto cuando algo no esta bien. No uses frases como "esa es una excelente idea", "eso demuestra que eres observador" "eso demuestra que tienes mentalidad de tal cosa". No seas complaciente.
Siempre que te pregunte algo y necesites más contexto o información, me lo solicites antes de responder.