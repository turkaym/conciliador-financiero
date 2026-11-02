import json
import hashlib
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("IDEMPOTENCY_MIDDLEWARE")

class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Solo protegemos operaciones transaccionales (mutaciones)
        if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if not redis:
            return await call_next(request)

        user_id = request.headers.get("Authorization", "anonymous")[:20]

        # Leemos el body para crear la firma criptográfica
        body_bytes = await request.body()
        body_hash = hashlib.sha256(body_bytes).hexdigest()

        # FIX ARQUITECTÓNICO: Si el front no manda el header, armamos un fallback
        # basado en la ruta y método para atajar el doble clic instintivo.
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            path = request.url.path
            idempotency_key = hashlib.md5(f"{request.method}:{path}".encode()).hexdigest()

        cache_key = f"idempotency:{user_id}:{idempotency_key}:{body_hash}"

        # Reinyectamos el body para que el framework pueda consumirlo después
        async def receive():
            return {"type": "http.request", "body": body_bytes}
        request._receive = receive

        # 1. Verificamos si la petición exacta fue procesada hace unos instantes
        cached_response = await redis.get(cache_key)
        if cached_response:
            logger.info(f"🛡️ [IDEMPOTENCY] Bloqueo de petición duplicada (Cache HIT): {cache_key}")
            data = json.loads(cached_response)
            return Response(
                content=data["body"],
                status_code=data["status_code"],
                headers={"Content-Type": "application/json", "X-Idempotent-Cache": "HIT"}
            )

        # 2. Candado de red (Lock) contra condición de carrera (doble clic simultáneo en milisegundos)
        # TTL ESTRICTO DE 5 SEGUNDOS según roadmap Fase D.
        is_processing = await redis.set(f"{cache_key}:lock", "locked", nx=True, ex=5)
        if not is_processing:
            logger.warning(f"⚠️ [IDEMPOTENCY] Carrera en red detectada. Petición bloqueada (Status 409).")
            return Response(
                content='{"detail": "Procesando transacción. Aguarde unos segundos antes de reintentar."}',
                status_code=409,
                media_type="application/json"
            )

        try:
            response: Response = await call_next(request)

            content_type = response.headers.get("content-type", "")
            # Excluimos descargas de archivos o Server-Sent Events del caché
            if "text/event-stream" in content_type or "application/octet-stream" in content_type:
                return response

            # Solo guardamos el resultado si no fue un error interno del servidor (500)
            if 200 <= response.status_code < 500:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                async def async_generator():
                    yield response_body

                response.body_iterator = async_generator()

                body_content = response_body.decode('utf-8')
                cache_payload = {"status_code": response.status_code, "body": body_content}

                # TTL ESTRICTO DE 5 SEGUNDOS para limpiar la RAM rápidamente y permitir
                # operaciones idénticas legítimas a futuro.
                await redis.setex(cache_key, 5, json.dumps(cache_payload))

            return response
        finally:
            await redis.delete(f"{cache_key}:lock")