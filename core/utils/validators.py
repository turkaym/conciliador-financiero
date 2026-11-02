import logging
from decimal import Decimal

logger = logging.getLogger("SECURITY_VALIDATOR")

class FileSecurityValidator:
    """
    Servicio encargado de auditar la integridad estructural de los archivos
    basándose en Magic Bytes y esquemas de codificación, evitando falsificaciones de extensión.
    """

    @staticmethod
    def is_safe_binary(file_path: str, extension: str) -> bool:
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(2048)
        except Exception as e:
            logger.error(f"❌ [VALIDADOR] Fallo I/O al intentar leer el archivo {file_path}: {e}")
            return False

        ext = extension.lower()

        if ext == '.xlsx':
            return chunk.startswith(b'PK\x03\x04')

        if ext == '.xls':
            return chunk.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')

        if ext in ['.csv', '.txt']:
            if b'\x00' in chunk:
                logger.warning(f"🛡️ [VALIDADOR] Bytes nulos detectados en un supuesto archivo de texto.")
                return False

            try:
                chunk.decode('utf-8')
                return True
            except UnicodeDecodeError:
                try:
                    chunk.decode('latin-1')
                    return True
                except Exception as encoding_err:
                    logger.warning(f"🛡️ [VALIDADOR] Falla de codificación de texto (No es UTF-8 ni Latin-1): {encoding_err}")
                    return False

        logger.warning(f"🛡️ [VALIDADOR] Extensión '{ext}' no soportada para la validación de integridad.")
        return False

# 🌟 FIX FASE A: Nuevo validador estricto para transacciones
class IntegridadContableValidator:
    @staticmethod
    def validar_paridad_movimiento(monto: Decimal, saldo_pendiente: Decimal, referencia: str) -> bool:
        if monto == Decimal('0.0'):
            raise ValueError(f"[BUSINESS_LOGIC] Transacción en cero detectada ({referencia}). Ingesta bloqueada.")

        if abs(monto) != abs(saldo_pendiente):
            raise ValueError(f"[BUSINESS_LOGIC] Descuadre en ingesta bancaria ({referencia}): El monto ({monto}) difiere del saldo inicial pendiente ({saldo_pendiente}). Riesgo de dinero fantasma.")
        return True