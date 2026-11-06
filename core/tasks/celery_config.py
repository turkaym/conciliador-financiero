import os
import logging
import threading
from functools import wraps
from celery import Celery
from celery.signals import setup_logging, task_prerun
from celery.schedules import crontab
from kombu import Queue, Exchange
from config.config import settings
from config.feature_flags import feature_flags

# ==========================================
# 🌟 FIX TRAZABILIDAD (Correlation ID Logger)
# ==========================================
_thread_local = threading.local()

class CorrelationIdFilter(logging.Filter):
    """Filtro para inyectar el Correlation ID en cada línea de log del Worker."""
    def filter(self, record):
        record.correlation_id = getattr(_thread_local, 'correlation_id', 'SYSTEM-CRON')
        return True

@task_prerun.connect
def inject_correlation_id(task_id, task, args, kwargs, **opts):
    """Intercepta la tarea un milisegundo antes de ejecutarse para robar el ID."""
    # Extrae el ID que envió FastAPI, o usa el task_id nativo de Celery como fallback
    _thread_local.correlation_id = kwargs.get('correlation_id', task_id)

@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Sobreescribe el logger por defecto de Celery con formato Enterprise."""
    from logging.config import dictConfig
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'correlation_id': {'()': CorrelationIdFilter}
        },
        'formatters': {
            'enterprise': {
                'format': '[%(asctime)s] [%(levelname)s] [Trace: %(correlation_id)s] [%(name)s] %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'enterprise',
                'filters': ['correlation_id']
            }
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO'
        }
    })

# ==========================================
# CEREBRO ASÍNCRONO DEL SISTEMA
# ==========================================
app = Celery("conciliador_tasks")

FEATURE_TASKS = {
    'core.tasks.maintenance_tasks.run_tenant_matching_task': 'reconciliation',
    'generar_asiento_conciliacion': 'reconciliation',
    'revertir_asiento_conciliacion': 'reconciliation',
    'core.tasks.ai_tasks.process_agent_message_task': 'ai_copilot',
    'core.tasks.webhooks_worker.dispatch_webhook': 'b2b_integrations',
}


_celery_task = app.task


def feature_controlled_registration(*args, **options):
    def register(function):
        feature = FEATURE_TASKS.get(options.get('name', f'{function.__module__}.{function.__name__}'))
        if feature:
            @wraps(function)
            def guarded(*task_args, **task_kwargs):
                if not feature_flags.usable(feature):
                    raise RuntimeError(f"Task disabled by feature manifest: {feature}")
                return function(*task_args, **task_kwargs)
            function = guarded
        return _celery_task(function, **options)

    if args and callable(args[0]):
        return register(args[0])
    return register


app.task = feature_controlled_registration

# 🌟 CAPA 3.2: Configuración de Dead Letter Exchange (DLX) confirmada
dlx_exchange = Exchange('dlx', type='direct')
dlx_args = {
    'x-dead-letter-exchange': 'dlx',
    'x-dead-letter-routing-key': 'dead_letter'
}

app.conf.update(
    broker_url=settings.RABBITMQ_URL,
    result_backend=settings.REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    result_expires=86400,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    broker_heartbeat=120,
    broker_connection_timeout=30,
    worker_cancel_long_running_tasks_on_connection_loss=False,

    broker_connection_retry_on_startup=True,
    task_track_started=True,

    task_queues=(
        Queue('default', routing_key='default', queue_arguments=dlx_args),
        Queue('afip_queue', routing_key='afip_queue', queue_arguments=dlx_args),
        Queue('matching_queue', routing_key='matching_queue', queue_arguments=dlx_args),
        Queue('accounting_queue', routing_key='accounting_queue', queue_arguments=dlx_args),
        Queue('webhooks_queue', routing_key='webhooks_queue', queue_arguments=dlx_args),
        # 🌟 NUEVO: Cola dedicada para el Agente y Procesamiento Vectorial
        Queue('ai_queue', routing_key='ai_queue', queue_arguments=dlx_args),
        Queue('dead_letters', exchange=dlx_exchange, routing_key='dead_letter'),
    ),
    task_default_queue='default',

    task_routes={
        'core.tasks.afip_tasks.*': {'queue': 'afip_queue'},
        'core.tasks.padrones_worker.*': {'queue': 'afip_queue'},
        'core.tasks.cotizacion_worker.*': {'queue': 'afip_queue'},

        'generar_asiento_conciliacion': {'queue': 'accounting_queue'},
        'revertir_asiento_conciliacion': {'queue': 'accounting_queue'},

        'core.tasks.banking_tasks.*': {'queue': 'accounting_queue'},
        'core.tasks.accounting.*': {'queue': 'accounting_queue'},
        'core.tasks.maintenance_tasks.run_tenant_fiscal_audit_task': {'queue': 'accounting_queue'},
        'core.tasks.maintenance_tasks.provision_new_tenant_task': {'queue': 'accounting_queue'},

        'core.tasks.maintenance_tasks.run_tenant_matching_task': {'queue': 'matching_queue'},
        'core.tasks.maintenance_tasks.sweep_tenant_zombies_task': {'queue': 'matching_queue'},
        'core.tasks.notification_tasks.*': {'queue': 'matching_queue'},

        # 🌟 NUEVO: Enrutamiento estricto hacia el Sidecar de IA
        'core.tasks.ai_tasks.*': {'queue': 'ai_queue'},

        'core.tasks.maintenance_tasks.meta_orchestrator_task': {'queue': 'default'},
        'core.tasks.webhooks_worker.*': {'queue': 'webhooks_queue'},
        'core.tasks.reversiones_tasks.*': {'queue': 'default'},
        '*': {'queue': 'default'}
    },

    imports=[
        'core.tasks.base_task',
        'core.tasks.notification_tasks',
        'core.tasks.banking_tasks',
        'core.tasks.afip_tasks',
        'core.tasks.maintenance_tasks',
        'core.tasks.padrones_worker',
        'core.tasks.cotizacion_worker',
        'core.tasks.webhooks_worker',
        'core.tasks.accounting',
        "core.tasks.billing_tasks",
        "core.tasks.reversiones_tasks",
    ] + (["core.tasks.ai_tasks"] if feature_flags.usable("ai_copilot") else [])
)

# ==========================================
# CRONS CENTRALIZADOS
# ==========================================
app.conf.beat_schedule = {
    'run-zombie-sweeper-every-hour': {
        'task': 'core.tasks.maintenance_tasks.meta_orchestrator_task',
        'schedule': crontab(minute='0'),
        'args': ('core.tasks.maintenance_tasks.sweep_tenant_zombies_task', 'matching_queue')
    },
    'run-fiscal-auditor-daily': {
        'task': 'core.tasks.maintenance_tasks.meta_orchestrator_task',
        'schedule': crontab(hour='3', minute='0'),
        'args': ('core.tasks.maintenance_tasks.run_tenant_fiscal_audit_task', 'accounting_queue')
    },
    'run-sincronizacion-moneda-diaria': {
        'task': 'core.tasks.cotizacion_worker.sincronizar_cotizacion_diaria',
        'schedule': crontab(hour='15', minute='30'),
        'args': ('tenant_20935449163', 'USD', 'BNA')
    }
}

if feature_flags.usable('reconciliation'):
    app.conf.beat_schedule['run-auto-matching-every-15-mins'] = {
        'task': 'core.tasks.maintenance_tasks.meta_orchestrator_task',
        'schedule': crontab(minute='*/15'),
        'args': ('core.tasks.maintenance_tasks.run_tenant_matching_task', 'matching_queue'),
        'kwargs': {'extra_kwargs': {'entidad_id': 1}}
    }

if feature_flags.usable('b2b_integrations'):
    app.conf.beat_schedule['run-outbox-sweeper-every-10-secs'] = {
        'task': 'core.tasks.maintenance_tasks.meta_orchestrator_task',
        'schedule': 10.0,
        'args': ('core.tasks.webhooks_worker.sweep_outbox_events_task', 'webhooks_queue')
    }
