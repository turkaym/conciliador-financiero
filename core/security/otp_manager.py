import random
import logging
from core.api.rate_limiter import redis_client

logger = logging.getLogger("OTP_ENGINE")

class OTPManager:
    """
    Motor efímero de One-Time Passwords basado en Redis.
    Garantiza alta velocidad O(1), auto-destrucción por TTL, atomicidad y prevención de Flooding.
    """
    OTP_TTL_SECONDS = 900  # 15 minutos de validez
    OTP_COOLDOWN_SECONDS = 60 # 1 minuto estricto entre solicitudes

    @staticmethod
    async def generate_otp(identifier: str) -> str:
        redis_key = f"otp:{identifier}"
        cooldown_key = f"otp_cooldown:{identifier}"

        try:
            # 🌟 FIX FLOODING: Verificación de Cooldown antes de generar nada
            if await redis_client.exists(cooldown_key):
                ttl_restante = await redis_client.ttl(cooldown_key)
                logger.warning(f"⚠️ [OTP] Intento de flooding mitigado para {identifier}. Cooldown: {ttl_restante}s")
                raise ValueError(f"Por favor espere {ttl_restante} segundos antes de solicitar un nuevo código.")

            secure_random = random.SystemRandom()
            otp_code = f"{secure_random.randint(0, 999999):06d}"

            # 🌟 FIX ATOMICIDAD: Usamos un pipeline para asegurar que ambas llaves se graben juntas
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.setex(redis_key, OTPManager.OTP_TTL_SECONDS, otp_code)
                pipe.setex(cooldown_key, OTPManager.OTP_COOLDOWN_SECONDS, "locked")
                await pipe.execute()

            logger.info(f"🔑 OTP generado para {identifier} (Expira en {OTPManager.OTP_TTL_SECONDS}s)")
            return otp_code

        except ValueError as ve:
            raise ve # Propagamos la validación de negocio limpiamente
        except Exception as e:
            logger.error(f"💥 Fallo crítico en motor Redis al generar OTP: {e}")
            raise RuntimeError("Servicio de validación temporalmente no disponible.")

    @staticmethod
    async def validate_otp(identifier: str, provided_otp: str) -> bool:
        redis_key = f"otp:{identifier}"
        cooldown_key = f"otp_cooldown:{identifier}"

        try:
            stored_otp = await redis_client.get(redis_key)

            if not stored_otp:
                return False

            if stored_otp == provided_otp:
                # 🛑 PULSO DE DESTRUCCIÓN: Eliminamos el código y liberamos el cooldown
                async with redis_client.pipeline(transaction=True) as pipe:
                    pipe.delete(redis_key)
                    pipe.delete(cooldown_key)
                    await pipe.execute()

                logger.info(f"✅ OTP validado y destruido exitosamente para {identifier}")
                return True

            return False
        except Exception as e:
            logger.error(f"💥 Fallo crítico en motor Redis al validar OTP: {e}")
            raise RuntimeError("Servicio de validación temporalmente no disponible.")