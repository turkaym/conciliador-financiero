import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from core.database.models_tenant import ReglaImpuesto, PadronFiscal, SecuenciaFiscal
from core.database.models.contabilidad import RegistroTributario
from core.schemas.tax_engine import ImpuestoCalculado, ReglaImpuestoCreate, ReglaImpuestoUpdate

logger = logging.getLogger("TAX_ENGINE")

class TaxEngineService:

    # ==========================================
    # ABM DE REGLAS FISCALES
    # ==========================================
    def listar_reglas(self, db: Session, entidad_id: int) -> List[ReglaImpuesto]:
        return db.query(ReglaImpuesto).filter(ReglaImpuesto.entidad_id == entidad_id).all()

    def crear_regla(self, db: Session, entidad_id: int, payload: ReglaImpuestoCreate) -> ReglaImpuesto:
        # Validación de duplicados lógicos
        existente = db.query(ReglaImpuesto).filter(
            ReglaImpuesto.entidad_id == entidad_id,
            ReglaImpuesto.tipo_impuesto == payload.tipo_impuesto,
            ReglaImpuesto.jurisdiccion == payload.jurisdiccion
        ).first()
        if existente:
            raise HTTPException(status_code=409, detail="Ya existe una regla para este impuesto y jurisdicción.")

        nueva_regla = ReglaImpuesto(entidad_id=entidad_id, **payload.model_dump())
        db.add(nueva_regla)
        db.commit()
        db.refresh(nueva_regla)
        return nueva_regla

    def actualizar_regla(self, db: Session, entidad_id: int, regla_id: int, payload: ReglaImpuestoUpdate) -> ReglaImpuesto:
        regla = db.query(ReglaImpuesto).filter(ReglaImpuesto.id == regla_id, ReglaImpuesto.entidad_id == entidad_id).first()
        if not regla:
            raise HTTPException(status_code=404, detail="Regla no encontrada.")

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(regla, key, value)

        db.commit()
        db.refresh(regla)
        return regla

    # ==========================================
    # MOTOR DE CÁLCULO
    # ==========================================
    def evaluar_retenciones(
        self, db: Session, entidad_id: int, cuit_sujeto: str, monto_base: Decimal, fecha_operacion: date
    ) -> List[ImpuestoCalculado]:
        impuestos_a_retener: List[ImpuestoCalculado] = []
        reglas = db.query(ReglaImpuesto).filter(ReglaImpuesto.entidad_id == entidad_id, ReglaImpuesto.is_active == True).all()

        if not reglas:
            return impuestos_a_retener

        cuit_sanitizado = "".join(filter(str.isdigit, cuit_sujeto)).strip()
        periodo_fiscal = fecha_operacion.strftime("%Y%m")

        for regla in reglas:
            if monto_base <= regla.monto_minimo_sujeto:
                continue

            alicuota_final = regla.alicuota_defecto
            origen = "DEFECTO"

            if regla.aplica_padron:
                padron_entry = db.query(PadronFiscal).filter(
                    PadronFiscal.cuit == cuit_sanitizado,
                    PadronFiscal.jurisdiccion == regla.jurisdiccion,
                    PadronFiscal.periodo == periodo_fiscal
                ).first()

                if padron_entry:
                    if "RETENCION" in regla.tipo_impuesto.upper():
                        alicuota_final = padron_entry.alicuota_retencion
                    elif "PERCEPCION" in regla.tipo_impuesto.upper():
                        alicuota_final = padron_entry.alicuota_percepcion
                    origen = "PADRON"

            if alicuota_final <= Decimal('0.0'):
                continue

            monto_impuesto = (monto_base * alicuota_final) / Decimal('100.0')
            monto_impuesto = monto_impuesto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # 🌟 FIX: Inyectamos el código de régimen dinámico
            codigo_regimen = getattr(regla, 'codigo_regimen_afip', 217)

            impuestos_a_retener.append(ImpuestoCalculado(
                tipo_impuesto=regla.tipo_impuesto,
                jurisdiccion=regla.jurisdiccion,
                codigo_regimen_afip=codigo_regimen,
                base_imponible=monto_base,
                alicuota_aplicada=alicuota_final,
                monto_impuesto=monto_impuesto,
                origen_alicuota=origen,
                cuenta_contable_id=regla.cuenta_contable_id,
                id_regla_aplicada=regla.id
            ))

        return impuestos_a_retener

    def consolidar_registros_tributarios(
        self, db: Session, entidad_id: int, clase_tributo: str, cuit_sujeto: str, razon_social_sujeto: str,
        fecha_registro: date, impuestos_calculados: List[ImpuestoCalculado], comprobante_id: Optional[int] = None,
        asiento_id: Optional[int] = None, numero_comprobante_origen: Optional[str] = None
    ) -> List[RegistroTributario]:

        if not impuestos_calculados:
            return []

        periodo_fiscal = fecha_registro.strftime("%Y%m")
        registros = []

        for imp in impuestos_calculados:
            numero_cert = None
            if clase_tributo == "RETENCION_EMITIDA":
                secuencia = db.query(SecuenciaFiscal).filter(
                    SecuenciaFiscal.entidad_id == entidad_id, SecuenciaFiscal.punto_venta == 1, SecuenciaFiscal.tipo_cbte == 999
                ).with_for_update().first()

                if not secuencia:
                    secuencia = SecuenciaFiscal(entidad_id=entidad_id, punto_venta=1, tipo_cbte=999, ultimo_numero=0)
                    db.add(secuencia)
                    db.flush()

                secuencia.ultimo_numero += 1
                numero_cert = f"{secuencia.punto_venta:04d}-{secuencia.ultimo_numero:08d}"

            registro = RegistroTributario(
                entidad_id=entidad_id,
                clase_tributo=clase_tributo,
                tipo_impuesto=imp.tipo_impuesto,
                jurisdiccion=imp.jurisdiccion,
                cuit_sujeto=cuit_sujeto,
                razon_social_sujeto=razon_social_sujeto,
                fecha_registro=fecha_registro,
                comprobante_id=comprobante_id,
                asiento_id=asiento_id,
                numero_comprobante_origen=numero_comprobante_origen,
                numero_certificado=numero_cert,
                base_imponible=imp.base_imponible,
                alicuota_aplicada=imp.alicuota_aplicada,
                monto_impuesto=imp.monto_impuesto,
                periodo_fiscal=periodo_fiscal,
                origen_alicuota=imp.origen_alicuota
            )
            # Inyección silenciosa del código de régimen temporal en el objeto para la exportación
            setattr(registro, '_codigo_regimen_dinamico', imp.codigo_regimen_afip)

            db.add(registro)
            registros.append(registro)

        db.flush()
        return registros

tax_engine_service = TaxEngineService()