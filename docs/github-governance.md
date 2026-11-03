# Gobierno del repositorio en GitHub

## Controles versionados

`CODEOWNERS` asigna todo el repositorio a `@turkaym` y `@HugoTcach`. Cuando GitHub exige revisión de Code Owners, la aprobación de cualquiera de los dos satisface la propiedad. El autor no puede aprobar su propio pull request; junto con una aprobación obligatoria, esto produce revisión mutua.

El workflow `Quality gates` se ejecuta en pull requests y pushes a `main`, usa sólo `contents: read`, cancela ejecuciones anteriores de la misma rama y publica dos checks:

- `Frontend quality`: `npm ci`, contratos de feature flags y AI Rules, build de producción y `npm audit --audit-level=high`. Las alertas low/moderate siguen visibles; high/critical fallan.
- `Backend and governance`: guard de rutas sensibles, dependencias Python mínimas, tests enfocados, compilación/import smoke y validación de Compose con un `.env` temporal no secreto que siempre se elimina.

El lint general no es requerido porque conserva deuda conocida. No se oculta ni se representa como verde.

## Paridad local

Desde la raíz del repositorio:

```bash
cd frontend/app && npm ci
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

## GOV-02: configuración remota pendiente

Crear para `main` un ruleset o protección equivalente con estas condiciones exactas:

- exigir pull request antes de fusionar, una aprobación y revisión de Code Owners;
- descartar aprobaciones obsoletas y exigir aprobación del último push revisable;
- exigir resolución de conversaciones y los checks `Frontend quality` y `Backend and governance`;
- bloquear force-push y eliminación de la rama;
- no conceder bypass no documentado.

En repositorios privados, la disponibilidad de rulesets, Code Owners y algunas reglas depende del plan de GitHub de la organización o cuenta. Hay que confirmar el plan y leer la regla efectiva después de configurarla. GOV-01 no hizo push, no abrió PR y no cambió settings, remotes ni identidad Git.

## Rollback

Revertir el commit de GOV-01 elimina únicamente CODEOWNERS, checks, scripts, dependencias CI y esta documentación. No modifica datos, secretos, contenedores ni configuración remota. GOV-02 se revierte por separado en GitHub tras autorización explícita.
