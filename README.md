# Conciliador financiero

Aplicación web multiempresa para administrar operaciones financieras de un tenant: directorio B2B, egresos y pagos, registros fiscales, equipo y reglas determinísticas. El MVP actual se ejecuta localmente con Docker Compose; no existe todavía un despliegue público verificado.

## Alcance actual

El estado autorizado se define en [`config/feature_flags.json`](config/feature_flags.json). Una capacidad es usable únicamente cuando está habilitada e implementada. La habilitación global no reemplaza la autorización del tenant ni los controles RBAC.

| Módulo | Identificador | Habilitado | Implementado | Usable en el MVP |
| --- | --- | ---: | ---: | ---: |
| Directorio B2B | `b2b_directory` | Sí | Sí | Sí |
| Egresos y pagos | `expenses_payments` | Sí | Sí | Sí |
| Registros fiscales | `tax_registries` | Sí | Sí | Sí |
| Gestión de equipo | `team` | Sí | Sí | Sí |
| Reglas determinísticas | `ai_rules` | Sí | Sí | Sí |
| Conciliación | `reconciliation` | No | Sí | No |
| Copiloto de IA | `ai_copilot` | No | Sí | No |
| Integraciones B2B | `b2b_integrations` | No | Sí | No |

`implementado` indica que existe código para la capacidad; no implica que esté autorizado para uso. Conciliación debe permanecer deshabilitada hasta que un cambio revisado modifique el manifiesto. Un manifiesto ausente, malformado, con claves duplicadas, desconocidas o incompletas, tipos no booleanos o versión no soportada impide el arranque. Una capacidad ausente en el frontend también se considera no usable: el comportamiento es *fail closed*.

## Arquitectura

| Componente | Responsabilidad | Ubicación o servicio |
| --- | --- | --- |
| Frontend | SPA React, navegación, guards de capacidad y proxy `/api` | `frontend/app`, servicio `frontend` sobre Nginx |
| API gateway y core | FastAPI, autenticación, RBAC, composición de rutas y dominio | `services/api-gateway`, `core`, servicio `api-gateway` |
| PostgreSQL | Base maestra y datos aislados por esquema de tenant | servicio `postgres`, migraciones en `alembic_master` y `alembic_tenants` |
| PgBouncer | Pool transaccional para API y workers | servicio `pgbouncer`; las migraciones usan PostgreSQL directo |
| Redis | Caché, rate limiting, denylist JWT, OTP y resultados Celery | servicio `redis` |
| RabbitMQ | Broker de tareas Celery | servicio `rabbitmq` |
| MinIO | Objetos y cargas financieras compatibles con S3 | servicio `minio`, cliente en `core/storage` |
| Workers Celery | Colas fiscal, contable, matching/general e IA | `worker-afip`, `worker-accounting`, `worker-matching`, `worker-ai` |
| Celery Beat | Programación periódica filtrada por capacidades | servicio `celery-beat`, configuración en `core/tasks/celery_config.py` |
| Flower | Observación local de workers | servicio `flower` |

La base maestra conserva usuarios y tenants. Cada tenant opera en su propio esquema PostgreSQL. La API y los workers acceden mediante PgBouncer; el servicio efímero `migrate` conecta directamente a PostgreSQL para aplicar DDL y aprovisionar el entorno local.

## Requisitos

- Git.
- Docker con el subcomando Compose v2 (`docker compose`). No se requiere instalar bases ni brokers en el host.
- Para reproducir los quality gates fuera de contenedores: Python 3.11 y Node.js 24 con npm.
- Recursos suficientes para PostgreSQL 16, Redis 7, RabbitMQ 3, MinIO, cuatro workers y la compilación Node 24. El frontend servido usa Nginx 1.27.

Las versiones anteriores provienen de los Dockerfiles, imágenes Compose y [workflow de calidad](.github/workflows/quality-gates.yml). Compose v2.40.3 fue la versión local validada, pero el repositorio no declara un mínimo más específico.

## Inicio local seguro

### 1. Preparar el entorno

Desde un clon nuevo, en la raíz del repositorio:

```bash
cp .env.example .env
```

En PowerShell, el equivalente es:

```powershell
Copy-Item .env.example .env
```

`.env` está ignorado por Git. Los valores de `.env.example` son marcadores de desarrollo y NO son secretos aptos para producción. Antes de iniciar, se deben reemplazar como mínimo:

- `SECRET_KEY` y `ENCRYPTION_KEY_MASTER`;
- `DB_PASSWORD`;
- `RABBITMQ_PASSWORD` y la misma contraseña dentro de `RABBITMQ_URL`;
- `MINIO_ROOT_PASSWORD` y `MINIO_SECRET_KEY`;
- `ADMIN_PASSWORD`;
- la contraseña incluida en `FLOWER_BASIC_AUTH`.

El siguiente comando funciona con Python 3, modifica solamente el `.env` ignorado, usa aleatoriedad criptográfica y no imprime valores. Ejecútelo una sola vez sobre la copia sin modificar:

```bash
python -c "from pathlib import Path; import base64, functools, os, secrets; p=Path('.env'); t=p.read_text(); db=secrets.token_urlsafe(36); mq=secrets.token_urlsafe(36); mini=secrets.token_urlsafe(36); admin=secrets.token_urlsafe(36); flower=secrets.token_urlsafe(36); pairs=[('generate-a-random-development-secret',secrets.token_urlsafe(48)),('generate-a-valid-fernet-key',base64.urlsafe_b64encode(os.urandom(32)).decode()),('generate-a-random-database-password',db),('generate-a-random-rabbitmq-password',mq),('amqp://conciliador:replace-me@rabbitmq:5672//',f'amqp://conciliador:{mq}@rabbitmq:5672//'),('generate-a-random-minio-password',mini),('generate-a-random-admin-password',admin),('admin:generate-a-random-flower-password',f'admin:{flower}')]; p.write_text(functools.reduce(lambda s,r:s.replace(*r),pairs,t))"
```

También se puede usar un gestor de contraseñas para generar y editar esos campos sin enviarlos a la terminal, al portapapeles compartido ni al historial. Cambie `ADMIN_EMAIL` por una identidad local controlada por el operador. Las claves opcionales `PROMETEO_API_KEY`, `OPENAI_API_KEY` y `CLOUDFLARE_TOKEN` pueden permanecer vacías mientras sus integraciones no se utilicen.

### 2. Construir e iniciar

```bash
docker compose -p conciliador-financiero-dev up -d --build
```

No se requiere ejecutar migraciones manuales. Antes de habilitar la API, el servicio `migrate` ejecuta:

```text
alembic -n master upgrade head
python init_db.py
```

El bootstrap es idempotente: aplica la base maestra, aprovisiona el tenant local y crea la cuenta administrativa a partir de `ADMIN_EMAIL` y `ADMIN_PASSWORD` sólo si todavía no existe. No registra ni muestra una contraseña predeterminada.

### 3. Verificar

```bash
docker compose -p conciliador-financiero-dev ps
curl --fail http://127.0.0.1:18000/health
curl --fail http://127.0.0.1:18000/v1/capabilities
curl --fail --output /dev/null http://127.0.0.1:15173/
```

En PowerShell, `curl` puede ser un alias. Use `curl.exe` con esos mismos argumentos o:

```powershell
Invoke-RestMethod http://127.0.0.1:18000/health
Invoke-RestMethod http://127.0.0.1:18000/v1/capabilities
Invoke-WebRequest http://127.0.0.1:15173/ -UseBasicParsing
```

La salud esperada de la API incluye `"status":"online"`; capacidades devuelve ocho registros sin secretos. `docker compose ... ps` debe mostrar `api-gateway` y `frontend` como `healthy`, además de los servicios de infraestructura.

### Puertos predeterminados

Todos los puertos publicados se limitan a `127.0.0.1`.

| Uso | URL o puerto del repositorio | Variable |
| --- | --- | --- |
| Frontend | `http://127.0.0.1:15173` | `FRONTEND_PORT` |
| API | `http://127.0.0.1:18000` | `API_PORT` |
| PgBouncer | `127.0.0.1:16432` | `PGBOUNCER_PORT` |
| Redis | `127.0.0.1:16379` | `REDIS_PORT` |
| RabbitMQ AMQP | `127.0.0.1:15672` | `RABBITMQ_PORT` |
| RabbitMQ UI | `http://127.0.0.1:15673` | `RABBITMQ_MANAGEMENT_PORT` |
| MinIO API | `http://127.0.0.1:19000` | `MINIO_API_PORT` |
| MinIO UI | `http://127.0.0.1:19001` | `MINIO_CONSOLE_PORT` |
| Flower | `http://127.0.0.1:15555` | `FLOWER_PORT` |

Estos son defaults versionados, no valores inferidos del equipo actual. El entorno local validado también expone API en `18000` y frontend en `15173`, pero cualquier equipo puede sobrescribirlos en su `.env`, por ejemplo:

```dotenv
API_PORT=28000
FRONTEND_PORT=25173
FRONTEND_URL=http://127.0.0.1:25173
CORS_ORIGINS=http://127.0.0.1:25173
```

Si se cambia MinIO, ajuste también `MINIO_EXTERNAL_URL`. Los servicios `cloudflare` y `traefik` pertenecen al perfil opcional `edge` y no se inician con el comando normal.

### Operación cotidiana

```bash
# Seguir logs de componentes concretos del proyecto
docker compose -p conciliador-financiero-dev logs -f --tail=200 api-gateway frontend migrate

# Reiniciar sin eliminar contenedores ni datos persistentes
docker compose -p conciliador-financiero-dev restart

# Detener y retirar contenedores/red; conserva los volúmenes nombrados
docker compose -p conciliador-financiero-dev down

# Volver a crear el stack conservando datos
docker compose -p conciliador-financiero-dev up -d --build
```

El nombre de proyecto evita operar sobre contenedores Compose ajenos. No use eliminación de volúmenes como parada ordinaria: borra bases, colas y objetos locales y exige una decisión explícita de recuperación desde cero.

## Autenticación y onboarding

No existe una cuenta pública ni una credencial demo segura. El acceso local inicial usa el `ADMIN_EMAIL` y `ADMIN_PASSWORD` que el operador definió en su `.env`; `migrate` los aprovisiona automáticamente mediante `init_db.py`.

El endpoint `/v1/auth/register` crea un tenant y una cuenta inactiva que requiere OTP. Como el Compose predeterminado no incluye un servidor SMTP, ese flujo necesita una integración de correo configurada por el operador. Para desarrollo local desde cero, use la cuenta bootstrap; para otros entornos, el operador debe aprovisionar y activar identidades de forma controlada.

## Feature flags

1. Modifique exclusivamente el booleano correspondiente en [`config/feature_flags.json`](config/feature_flags.json).
2. Revise el diff y ejecute las pruebas de paridad de flags.
3. Para Conciliación, abra un cambio revisado; no la active mediante `.env` ni sólo desde la UI.
4. Reconstruya API, frontend, workers y Beat con `docker compose -p conciliador-financiero-dev up -d --build`.
5. Compruebe `/v1/capabilities`, rutas visibles, rutas API y programación de Beat.

Ocultar navegación no constituye autorización. La composición se aplica en las rutas del frontend, el montaje de routers FastAPI, el registro/guard de tareas Celery y los schedules de Beat. Después actúan, de forma independiente, el entitlement del tenant, la autenticación y RBAC. Si una capa no reconoce una capacidad, debe denegarla.

## Calidad y pruebas

Los comandos de paridad con [`.github/workflows/quality-gates.yml`](.github/workflows/quality-gates.yml) son:

```bash
cd frontend/app
npm ci
node --experimental-strip-types src/featureFlags.test.ts
node --experimental-strip-types src/features/ai-rules/aiRules.test.ts
npm run build
npm audit --audit-level=high
cd ../..

python -m pip install -r services/api-gateway/requirements-ci.txt
python -m unittest tests.test_feature_flags tests.test_feature_composition tests.test_ai_rules
python -m compileall -q config core services/api-gateway tests scripts/ci
python -c "from config.feature_flags import feature_flags; from core.api.v1.endpoints.ai_rules import router; assert feature_flags.usable('ai_rules') and router"
python scripts/ci/check_sensitive_paths.py BASE_SHA HEAD_SHA
bash scripts/ci/check_compose_config.sh
```

`npm audit --audit-level=high` falla ante avisos high/critical; los avisos low/moderate permanecen visibles. El lint general (`npm run lint`) conserva deuda conocida y no forma parte del gate: no debe describirse como verde. `check_compose_config.sh` requiere Bash, crea un `.env` temporal de CI y restaura el `.env` local mediante un trap.

La presencia del workflow y de estos resultados locales no demuestra que GitHub Actions se haya ejecutado en el hosting.

## Seguridad y datos

- `.env`, variantes `.env.*`, certificados, claves privadas y formatos de certificados están ignorados; sólo `.env.example` se versiona.
- `tenants_data`, uploads, logs, bases locales, dumps y volúmenes de runtime también están excluidos.
- Los CSV financieros, adjuntos, objetos MinIO y datos reales de tenants nunca deben incorporarse a Git.
- No use datos de producción para pruebas locales ni pegue archivos de entorno completos en issues, documentación o logs compartidos.
- Si un secreto aparece en Git, logs o mensajería, revoque o rote primero la credencial en el sistema emisor; luego retire la exposición y audite su uso. Borrar el texto no invalida el secreto.
- Las claves de `.env.example` son marcadores, no valores seguros para despliegue.

## Contribución y revisión

Trabaje en una rama, mantenga cada commit como una unidad revisable, ejecute los checks relevantes y use mensajes Conventional Commits. La política detallada está en [`docs/github-governance.md`](docs/github-governance.md).

El repositorio incluye `CODEOWNERS` para revisión de propiedad y el workflow `Quality gates`. La protección/ruleset remoto, los checks requeridos y la ejecución alojada siguen pendientes de autorización y configuración; la presencia de archivos versionados no habilita esos controles en GitHub por sí sola.

## Solución de problemas

### Conflicto de puertos

Cambie sólo los puertos publicados en `.env` (`API_PORT`, `FRONTEND_PORT`, etc.) y mantenga coherentes `FRONTEND_URL`, `CORS_ORIGINS` y `MINIO_EXTERNAL_URL`. Después recree los servicios. No cambie los puertos internos de la red Compose.

### Contenedor no saludable

```bash
docker compose -p conciliador-financiero-dev ps
docker compose -p conciliador-financiero-dev logs --tail=200 postgres pgbouncer redis rabbitmq migrate api-gateway frontend
```

Resuelva primero el servicio dependiente más bajo. API y frontend esperan healthchecks; `migrate` debe terminar con código cero.

### Migración o bootstrap fallido

```bash
docker compose -p conciliador-financiero-dev logs --tail=200 migrate postgres
docker compose -p conciliador-financiero-dev run --rm migrate
```

El segundo comando vuelve a ejecutar el proceso idempotente. Verifique placeholders pendientes, conectividad directa a `postgres` y estado de Alembic antes de modificar datos manualmente.

### Workers sin conectividad

```bash
docker compose -p conciliador-financiero-dev logs --tail=200 rabbitmq redis worker-afip worker-accounting worker-matching worker-ai celery-beat
docker compose -p conciliador-financiero-dev exec worker-matching celery -A core.tasks.celery_config inspect ping
```

Revise que `RABBITMQ_PASSWORD` coincida con `RABBITMQ_URL` y que los hosts internos sigan siendo `rabbitmq` y `redis`, no `127.0.0.1`.

### Dependencias obsoletas

Use `npm ci`, no `npm install`, para reproducir el lockfile. Si la imagen conserva capas anteriores, ejecute nuevamente `up -d --build`; no edite dependencias dentro de un contenedor en ejecución.

### Diferencia entre UI y API

Compare `config/feature_flags.json` con `/v1/capabilities`, reconstruya frontend/API/workers/Beat y descarte assets antiguos del navegador. Una capacidad global usable todavía puede quedar bloqueada por entitlement del tenant o RBAC; eso no es un fallo del manifiesto.

### Windows, Git Bash y PowerShell

Los comandos `cp`, `cd ... && ...`, `/dev/null` y los scripts `.sh` requieren Git Bash/WSL. En PowerShell use `Copy-Item`, ejecute cada cambio de directorio por separado, use `$null` o los cmdlets web y lance `check_compose_config.sh` desde Git Bash. Los comandos `docker compose` son iguales en ambos shells.

## Estado y limitaciones

- El stack local `conciliador-financiero-dev` fue validado con API y frontend saludables y ocho capacidades coherentes con el manifiesto.
- No se recreó un clon limpio ni se eliminaron volúmenes para probar el primer arranque; se validaron la configuración Compose, el bootstrap declarado y los comandos no destructivos contra el stack persistente actual.
- No hay despliegue público verificado ni evidencia de ejecución alojada de CI.
- El audit de npm puede conservar avisos moderate/low; el gate sólo rechaza high/critical.
- El lint general del frontend tiene deuda conocida y no está verde.
- CODEOWNERS y CI están versionados, pero las reglas remotas todavía no están habilitadas.
- Conciliación, Copiloto de IA e Integraciones B2B permanecen deshabilitados aunque exista código implementado.
