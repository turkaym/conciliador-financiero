import logging
import redis
import threading
from functools import wraps
from celery.exceptions import Ignore
from config.config import settings

logger = logging.getLogger("REDIS_LOCK")
redis_client = redis.from_url(settings.REDIS_URL)

def redis_lock(key_prefix: str, timeout: int = 30, extend_interval: int = 20):
    """
    Decorador Zero-Zombie: Previene Doble Ejecución.
    Implementa un Watchdog que auto-extiende el TTL del candado mientras
    el worker siga vivo, evadiendo bloqueos infinitos si el contenedor crashea.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            tenant_id = kwargs.get('tenant_id', 'global')
            object_name = kwargs.get('object_name', self.request.id)
            lock_id = f"mutex:{key_prefix}:{tenant_id}:{object_name}"

            # 1. Adquirimos candado con TTL corto (30s)
            task_lock = redis_client.lock(lock_id, timeout=timeout, blocking=False)
            if not task_lock.acquire():
                logger.warning(f"🔒 [MUTEX] Ejecución duplicada detectada. Abortando silenciosamente: {lock_id}")
                raise Ignore()

            # 2. Inicializamos el Watchdog Thread
            stop_event = threading.Event()

            def watchdog():
                # Mientras no se dé la orden de detener, espera 20s y renueva el candado
                while not stop_event.wait(extend_interval):
                    try:
                        if task_lock.owned():
                            task_lock.reacquire()
                    except Exception as e:
                        logger.error(f"⚠️ [WATCHDOG] Fallo al renovar candado {lock_id}: {e}")
                        break

            watchdog_thread = threading.Thread(target=watchdog, daemon=True)
            watchdog_thread.start()

            # 3. Ejecución de la Lógica de Negocio
            try:
                return func(self, *args, **kwargs)
            finally:
                # 4. Apagado elegante: Detenemos el hilo y liberamos el candado
                stop_event.set()
                watchdog_thread.join(timeout=1.0)
                try:
                    if task_lock.owned():
                        task_lock.release()
                except Exception as e:
                    logger.error(f"❌ [MUTEX] Fallo al liberar candado en Redis: {e}")

        return wrapper
    return decorator