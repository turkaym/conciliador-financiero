import os
import time
import logging
import redis
from datetime import datetime
from decimal import Decimal, InvalidOperation
from zeep import Client, Settings
from zeep.cache import SqliteCache, InMemoryCache
from zeep.transports import Transport
from requests import Session
from .auth import AfipAuthManager
from abc import ABC, abstractmethod
from core.utils.enums import TipoComprobanteAFIP

logger = logging.getLogger("AFIP_WSFE")

# 🌟 CONEXIÓN GLOBAL A REDIS (Candado Distribuido)
redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True
)

class BaseFiscalProvider(ABC):
    @abstractmethod
    def get_last_voucher_number(self, punto_venta: int, tipo_cbte: int) -> int:
        pass

    @abstractmethod
    def get_voucher_details(self, nro: int, punto_venta: int, tipo_cbte: int) -> dict:
        pass

class AfipWSFEClient(BaseFiscalProvider):
    def __init__(self, auth_manager: AfipAuthManager, cuit: str):
        self.auth = auth_manager
        self.cuit = cuit
        self.environment = auth_manager.environment

        self.wsdl = (
            "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
            if self.environment == "prod"
            else "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
        )

        self.http_session = Session()

        # 🌟 FIX DEFINITIVO I/O: Usamos memoria RAM para el WSDL.
        # Cero problemas de permisos, cero I/O de disco.
        transport = Transport(
            cache=InMemoryCache(timeout=86400), # Caché en RAM por 24hs
            session=self.http_session,
            timeout=30
        )
        settings = Settings(strict=False, xml_huge_tree=True)
        self.client = Client(self.wsdl, transport=transport, settings=settings)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.http_session.close()

    def _safe_decimal(self, value) -> Decimal:
        if value is None or value == "":
            return Decimal('0.0')
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, InvalidOperation):
            logger.warning(f"⚠️ [AFIP] Valor numérico anómalo detectado y saneado: {value}")
            return Decimal('0.0')

    def _format_afip_date(self, afip_date: str) -> str:
        if not afip_date: return None
        date_str = str(afip_date).strip()
        if len(date_str) != 8: return date_str
        try: return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError: return date_str

    def _get_auth_payload(self, force_refresh: bool = False):
        """
        Negocia el token WSAA aplicando un candado distribuido (Redis).
        Previene bloqueos del fisco por saturación (DDoS involuntario)
        cuando múltiples workers de Celery procesan el mismo CUIT en paralelo.
        """
        lock_key = f"afip_wsaa_lock_{self.cuit}"

        # Intentamos adquirir el candado por 15 segundos
        acquired = redis_client.set(lock_key, "locked", nx=True, ex=15)

        if not acquired and force_refresh:
            logger.warning(f"⏳ [AFIP] Otro worker está negociando el token para el CUIT {self.cuit}. Esperando...")
            time.sleep(3) # Backoff preventivo

        try:
            credentials = self.auth.get_token(self.cuit, force_refresh=force_refresh)
        except TypeError:
            if force_refresh and hasattr(self.auth, 'clear_cache'):
                self.auth.clear_cache(self.cuit)
            credentials = self.auth.get_token(self.cuit)
        finally:
            # Liberamos el candado SI y SOLO SI fuimos nosotros quienes lo tomamos
            if acquired:
                redis_client.delete(lock_key)

        return {
            "Token": credentials.token,
            "Sign": credentials.sign,
            "Cuit": self.cuit
        }

    # =========================================================
    # 🌟 ENVOLTORIO DE REINTENTOS PARA LOTES MASIVOS
    # =========================================================
    def _execute_with_retry(self, operation, **kwargs):
        try:
            return operation(force_refresh=False, **kwargs)
        except ValueError as e:
            if "600" in str(e) or "ValidacionDeToken" in str(e):
                logger.warning("⚠️ [AFIP] Token expirado en medio del lote. Forzando regeneración criptográfica...")
                return operation(force_refresh=True, **kwargs)
            raise

    def get_last_voucher_number(self, punto_venta: int, tipo_cbte: int) -> int:
        return self._execute_with_retry(self._do_get_last_voucher, punto_venta=punto_venta, tipo_cbte=tipo_cbte)

    def get_voucher_details(self, nro: int, punto_venta: int, tipo_cbte: int):
        return self._execute_with_retry(self._do_get_voucher_details, nro=nro, punto_venta=punto_venta, tipo_cbte=tipo_cbte)

    # =========================================================

    def _do_get_last_voucher(self, force_refresh: bool, punto_venta: int, tipo_cbte: int) -> int:
        auth_payload = self._get_auth_payload(force_refresh)
        try:
            response = self.client.service.FECompUltimoAutorizado(
                Auth=auth_payload, PtoVta=punto_venta, CbteTipo=tipo_cbte
            )
            self._check_errors(response)
            return response.CbteNro
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"💥 Error en FECompUltimoAutorizado: {e}")
            raise RuntimeError(f"Fallo de comunicación WSFE: {str(e)}")

    def _do_get_voucher_details(self, force_refresh: bool, nro: int, punto_venta: int, tipo_cbte: int):
        auth_payload = self._get_auth_payload(force_refresh)
        request_data = {"CbteTipo": tipo_cbte, "CbteNro": nro, "PtoVta": punto_venta}

        try:
            response = self.client.service.FECompConsultar(Auth=auth_payload, FeCompConsReq=request_data)
            self._check_errors(response)
            data = response.ResultGet

            # Desglose de arrays
            importe_iva = Decimal('0.0')
            detalles_iva = []
            if hasattr(data, 'Iva') and data.Iva and hasattr(data.Iva, 'AlicIva'):
                alic_ivas = data.Iva.AlicIva if isinstance(data.Iva.AlicIva, list) else [data.Iva.AlicIva]
                for iva in alic_ivas:
                    if iva is not None:
                        imp = self._safe_decimal(getattr(iva, 'Importe', '0.0'))
                        importe_iva += imp
                        detalles_iva.append({
                            "id_alicuota_afip": int(iva.Id),
                            "base_imponible": self._safe_decimal(getattr(iva, 'BaseImp', '0.0')),
                            "importe": imp
                        })

            importe_tributos = Decimal('0.0')
            detalles_tributos = []
            if hasattr(data, 'Tributos') and data.Tributos and hasattr(data.Tributos, 'Tributo'):
                tributos = data.Tributos.Tributo if isinstance(data.Tributos.Tributo, list) else [data.Tributos.Tributo]
                for trib in tributos:
                    if trib is not None:
                        imp = self._safe_decimal(getattr(trib, 'Importe', '0.0'))
                        importe_tributos += imp
                        detalles_tributos.append({
                            "id_tributo_afip": int(trib.Id),
                            "descripcion": getattr(trib, 'Desc', None),
                            "base_imponible": self._safe_decimal(getattr(trib, 'BaseImp', '0.0')),
                            "alicuota": self._safe_decimal(getattr(trib, 'Alic', '0.0')),
                            "importe": imp
                        })

            comprobantes_asociados = []
            if hasattr(data, 'CbtesAsoc') and data.CbtesAsoc and hasattr(data.CbtesAsoc, 'CbteAsoc'):
                asociados = data.CbtesAsoc.CbteAsoc if isinstance(data.CbtesAsoc.CbteAsoc, list) else [data.CbtesAsoc.CbteAsoc]
                for asoc in asociados:
                    if asoc is not None:
                        cuit_asoc = getattr(asoc, 'Cuit', getattr(data, 'DocNro', self.cuit))
                        comprobantes_asociados.append({
                            "tipo_cbte_afip": asoc.Tipo,
                            "punto_venta": asoc.PtoVta,
                            "numero": asoc.Nro,
                            "cuit": str(cuit_asoc)
                        })

            importe_neto = self._safe_decimal(getattr(data, 'ImpNeto', '0.0'))
            importe_exento = self._safe_decimal(getattr(data, 'ImpOpEx', '0.0'))
            importe_total = self._safe_decimal(getattr(data, 'ImpTotal', '0.0'))
            cotizacion = self._safe_decimal(getattr(data, 'MonCotiz', '1.0'))

            clase_doc = TipoComprobanteAFIP.get_clase(tipo_cbte).value

            return {
                "tipo_cbte_afip": tipo_cbte,
                "clase_documento": clase_doc,
                "punto_venta": punto_venta,
                "numero": nro,
                "fecha_emision": self._format_afip_date(data.CbteFch),
                "cuit_emisor": self.cuit,
                "cuit_receptor": data.DocNro,
                "importe_neto": importe_neto,
                "importe_iva": importe_iva,
                "importe_tributos": importe_tributos,
                "importe_exento": importe_exento,
                "importe_total": importe_total,
                "moneda": data.MonId,
                "cotizacion": cotizacion,
                "cae": getattr(data, 'CodAutorizacion', None),
                "vencimiento_cae": self._format_afip_date(getattr(data, 'FchVto', None)),
                "detalles_iva": detalles_iva,
                "detalles_tributos": detalles_tributos,
                "comprobantes_asociados": comprobantes_asociados
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"💥 Error al consultar comprobante detallado {nro}: {e}")
            raise RuntimeError(f"Fallo en FECompConsultar: {str(e)}")

    def _check_errors(self, response):
        if hasattr(response, 'Errors') and response.Errors:
            err = response.Errors.Err[0]
            error_msg = f"Cod {err.Code}: {err.Msg}"
            logger.error(f"❌ ARCA Error Estructural: {error_msg}")
            raise ValueError(f"Rechazo de Negocio ARCA ({err.Code}): {err.Msg}")

        if hasattr(response, 'ResultGet') and hasattr(response.ResultGet, 'Observaciones'):
            if response.ResultGet.Observaciones:
                obs = response.ResultGet.Observaciones.Obs[0]
                logger.warning(f"⚠️ Observación Fiscal ARCA: {obs.Msg}")