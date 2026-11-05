from abc import ABC, abstractmethod
from typing import List, Generator
from fastapi import HTTPException

from core.database.models_tenant import LotePago, LotePagoDetalle


class BaseExportAdapter(ABC):
    """
    Contrato base para fábricas de exportación bancaria.
    """
    @abstractmethod
    def generar_archivo(self, lote: LotePago, detalles: List[LotePagoDetalle]) -> Generator[str, None, None]:
        pass


class InterbankingAdapter(BaseExportAdapter):
    """
    Generador de formato posicional (.txt) para la red Interbanking.
    Ejecuta validaciones matemáticas sincrónicas y construcción asíncrona mediante Streaming TCP Puro (Zero-RAM).
    """
    def generar_archivo(self, lote: LotePago, detalles: List[LotePagoDetalle]) -> Generator[str, None, None]:
        # ==============================================================================
        # 1. ESCUDO FAIL-FAST PERIMETRAL (Sincrónico)
        # ==============================================================================

        # A) Validación Estricta de la Cuenta de Origen (Débito)
        # 🌟 FIX ARQUITECTURA: Se apunta a la relación 'cuenta_tesoreria' de la nueva BD
        cuenta_origen = getattr(lote, 'cuenta_tesoreria', None)
        if not cuenta_origen:
            raise HTTPException(
                status_code=422,
                detail="Exportación abortada. El lote no posee una cuenta de tesorería de origen asignada para el débito."
            )

        # 🌟 FIX ARQUITECTURA: La columna correcta en CuentaTesoreria es 'cbu_cvu'
        cbu_origen = getattr(cuenta_origen, 'cbu_cvu', getattr(cuenta_origen, 'numero_cuenta', None))
        if not cbu_origen or len(str(cbu_origen)) != 22 or not str(cbu_origen).isdigit():
            raise HTTPException(
                status_code=422,
                detail=f"Exportación abortada. La caja/cuenta de origen no posee un CBU válido de 22 dígitos. (Valor hallado: {cbu_origen})"
            )

        # B) Validación Estricta de Proveedores y Cuentas Destino (Crédito)
        for detalle in detalles:
            proveedor = None
            if detalle.orden_pago and detalle.orden_pago.proveedor:
                proveedor = detalle.orden_pago.proveedor
            elif detalle.comprobante:
                pass # Fallback reservado para futuras arquitecturas

            if proveedor:
                cbu_destino = getattr(proveedor, 'cbu', None)
                # 🌟 FIX NEGOCIO: Bloqueamos estrictamente los CBUs "dummy" de ceros
                if not cbu_destino or len(str(cbu_destino)) != 22 or not str(cbu_destino).isdigit() or str(cbu_destino) == "0000000000000000000000":
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Exportación abortada. El proveedor '{proveedor.razon_social}' "
                            f"(CUIT: {proveedor.cuit}) posee un CBU inválido, nulo o compuesto por ceros (Dummy). "
                            "Corrija el legajo maestro en el Directorio B2B antes de generar la remesa."
                        )
                    )

        # ==============================================================================
        # 2. CONSTRUCCIÓN STREAMING: Generador Aislado (Closure)
        # ==============================================================================
        def _stream_generator() -> Generator[str, None, None]:
            # Cabecera posicional estándar Interbanking
            fecha_lote = lote.fecha_autorizacion.strftime("%Y%m%d") if lote.fecha_autorizacion else "00000000"
            codigo_truncado = lote.codigo_lote[:15].ljust(15)
            yield f"*DATOS*{codigo_truncado}{fecha_lote}{cbu_origen}\n"

            # Cuerpo posicional de transferencias
            for detalle in detalles:
                if detalle.orden_pago and detalle.orden_pago.proveedor:
                    prov = detalle.orden_pago.proveedor

                    # Formateo a 16 caracteres para que al quitar el punto queden exactamente 15.
                    importe_str = f"{detalle.monto_asignado_ars:016.2f}".replace('.', '')
                    referencia = detalle.orden_pago.codigo_trazabilidad[:15].ljust(15)

                    yield f"{prov.cuit}{prov.cbu}{importe_str}{referencia}\n"

        return _stream_generator()