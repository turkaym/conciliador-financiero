import logging
from fastapi import Request, HTTPException, status, Header
import redis.asyncio as redis
from config.config import settings

logger = logging.getLogger("RATE_LIMITER")

# 🌟 FIX ARQUITECTURA: Cliente Redis Global (Requerido por OTPManager y Workers)
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

class RateLimiter:
    """
    Limitador de peticiones basado en conteo atómico usando Redis.
    Aísla las restricciones por Tenant para evitar abuso de recursos.
    """
    def __init__(self, action: str, limit_seconds: int = 30, max_requests: int = 100):
        self.action = action
        self.limit_seconds = limit_seconds
        self.max_requests = max_requests

    async def __call__(self, request: Request, x_entity_id: str = Header(..., alias="X-Entity-ID")):
        # ⚠️ ADVERTENCIA ARQUITECTÓNICA: Usar X-Entity-ID permite Spoofing.
        # Solo usar para endpoints públicos (ej. webhooks). Para endpoints privados,
        # el ID debe venir de `current_user.tenant.schema_name` validado en dependencias.
        redis = request.app.state.redis
        key = f"ratelimit:tenant:{self.action}:{x_entity_id}"

        try:
            # Pipeline garantiza que INCR y EXPIRE se ejecuten atómicamente
            async with redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, self.limit_seconds, nx=True)
                result = await pipe.execute()

            current = result[0]

            if current > self.max_requests:
                ttl = await redis.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Límite operativo del espacio de trabajo alcanzado. Aguarde {ttl} segundos antes de solicitar '{self.action}'."
                )
        except HTTPException:
            raise
        except Exception as e:
            # Patrón Fail-Open: Si Redis colapsa, dejamos operar al ERP.
            logger.error(f"⚠️ Falla en motor Redis (RateLimiter Tenant): {e}")
            pass

class IPRateLimiter:
    """
    Limitador perimetral de peticiones basado en la Dirección IP.
    Protege endpoints públicos (Login, Register) contra fuerza bruta y DoS.
    """
    def __init__(self, action: str, limit_seconds: int = 60, max_requests: int = 5):
        self.action = action
        self.limit_seconds = limit_seconds
        self.max_requests = max_requests

    async def __call__(self, request: Request):
        redis = request.app.state.redis

        # 🌟 FIX SEGURIDAD: Prioridad estricta al WAF perimetral (Cloudflare)
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            ip = cf_ip.strip()
        else:
            # Fallback a proxy tradicional con limpieza estricta
            forwarded = request.headers.get("X-Forwarded-For")
            ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "127.0.0.1")

        key = f"ratelimit:ip:{self.action}:{ip}"

        try:
            async with redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, self.limit_seconds, nx=True)
                result = await pipe.execute()

            current = result[0]

            if current > self.max_requests:
                ttl = await redis.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Se detectó tráfico anómalo. Bloqueo de seguridad activado por {ttl} segundos.",
                    headers={"Retry-After": str(ttl if ttl > 0 else self.limit_seconds)}
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"⚠️ Falla en motor Redis (IPRateLimiter): {e}")
            pass