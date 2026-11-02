import logging
import requests
from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from core.database.models.contabilidad import HistorialCotizacion

logger = logging.getLogger("ORACULO_CAMBIARIO")

class CotizacionService:
    def __init__(self):
        # En producción esto apuntaría a un servicio BNA oficial o WSFE AFIP
        self.api_url = "https://dolarapi.com/v1/dolares/oficial"
        self.timeout = 5.0 # Timeout corto para no bloquear las transacciones de los usuarios

    def _fetch_external_fx_rate(self) -> dict:
        """Obtiene la cotización en tiempo real desde una API externa (Fallback)."""
        try:
            logger.info("📡 [ORÁCULO] Consultando cotización oficial en tiempo real...")
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            compra = Decimal(str(data.get("compra", 0)))
            venta = Decimal(str(data.get("venta", 0)))

            if venta <= Decimal('0.0'):
                raise ValueError("La API externa devolvió una cotización cero o negativa.")

            return {"compra": compra, "venta": venta}
        except Exception as e:
            logger.error(f"❌ [ORÁCULO] Fallo consultando API externa: {e}")
            raise ValueError(f"No se pudo obtener la cotización en tiempo real: {e}")

    def obtener_cotizacion_oficial_segura(self, db: Session, moneda: str, fecha_operacion: date) -> Decimal:
        """
        Patrón Read-Through Cache.
        1. Intenta leer de la base de datos (Rápido).
        2. Si falla, hace Fetch externo (Lento).
        3. Si el Fetch funciona, lo guarda en BD para la próxima vez y lo devuelve.
        4. Si todo falla, lanza una excepción (Fail-Closed).
        """
        if moneda == "ARS":
            return Decimal("1.0")

        # 1. Caché L1: Base de Datos
        cotizacion_db = db.query(HistorialCotizacion).filter(
            HistorialCotizacion.moneda == moneda,
            HistorialCotizacion.fecha <= fecha_operacion
        ).order_by(HistorialCotizacion.fecha.desc()).first()

        if cotizacion_db:
            return cotizacion_db.cotizacion_venta

        logger.warning(f"⚠️ [ORÁCULO] Caché Miss en Base de Datos para {moneda} el {fecha_operacion}. Intentando Fallback externo.")

        # 2. Caché Miss: Llama a la API Externa (Oráculo On-the-Fly)
        try:
            cotizacion_externa = self._fetch_external_fx_rate()

            # 3. Persistir en la BD (Write-Through) usando UPSERT para evitar condiciones de carrera
            origen = "BNA_JIT" # Marcamos que se obtuvo Just-In-Time
            stmt = insert(HistorialCotizacion).values(
                moneda=moneda,
                fecha=fecha_operacion,
                cotizacion_compra=cotizacion_externa["compra"],
                cotizacion_venta=cotizacion_externa["venta"],
                origen=origen
            )

            stmt = stmt.on_conflict_do_update(
                index_elements=['moneda', 'fecha', 'origen'],
                set_={
                    'cotizacion_compra': stmt.excluded.cotizacion_compra,
                    'cotizacion_venta': stmt.excluded.cotizacion_venta
                }
            )

            db.execute(stmt)
            # Hacemos flush para que la transacción actual la vea si es necesario,
            # pero el commit final lo hace la función llamadora (ej. crear_orden_pago)
            db.flush()

            logger.info(f"✅ [ORÁCULO] Cotización {moneda} guardada JIT en BD: {cotizacion_externa['venta']}")
            return cotizacion_externa["venta"]

        except ValueError as ve:
            # 4. Fail-Closed: No hay datos locales y la API falló. Bloqueamos.
            logger.critical(f"🔥 [ORÁCULO] Imposible obtener cotización para {moneda}. Transacción rechazada.")
            raise ValueError(f"Falla crítica del Oráculo Cambiario: {str(ve)}")

cotizacion_service = CotizacionService()