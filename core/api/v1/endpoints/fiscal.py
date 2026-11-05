import logging
from typing import Optional, Annotated, List
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Header
from sqlalchemy.orm import Session

from core.api.deps import get_current_user, CachedUser, EntityRoleChecker, get_tenant_db_session
from core.database.models.contabilidad import RegistroTributario
from core.database.models_tenant import ContactoComercial, Comprobante
from core.schemas.tax_engine import LineaExportacionSIRE, ReglaImpuestoCreate, ReglaImpuestoUpdate, ReglaImpuestoResponse
from core.schemas.pagos import SimularRetencionRequest, SimularRetencionResponse, RetencionDetalleResponse
from core.utils.txt_exporter import FixedWidthFileGenerator
from core.services.tax_engine_service import tax_engine_service

logger = logging.getLogger("API_FISCAL")

# 🌟 FIX PERIMETRAL: Blindaje global del router para evitar fugas
router = APIRouter(
    tags=["Gestión Tributaria y DDJJ"],
    dependencies=[Depends(EntityRoleChecker(["admin", "dueño", "operador"]))]
)

# ==========================================
# ABM DE REGLAS IMPOSITIVAS
# ==========================================
@router.get("/reglas", response_model=List[ReglaImpuestoResponse])
def listar_reglas(
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session)
):
    return tax_engine_service.listar_reglas(db, x_entity_id)

@router.post("/reglas", response_model=ReglaImpuestoResponse, dependencies=[Depends(EntityRoleChecker(["admin", "dueño"]))])
def crear_regla(
    payload: ReglaImpuestoCreate,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session)
):
    return tax_engine_service.crear_regla(db, x_entity_id, payload)

@router.patch("/reglas/{regla_id}", response_model=ReglaImpuestoResponse, dependencies=[Depends(EntityRoleChecker(["admin", "dueño"]))])
def actualizar_regla(
    regla_id: int,
    payload: ReglaImpuestoUpdate,
    x_entity_id: Annotated[int, Header(description="ID de la Razón Social Activa")],
    db: Session = Depends(get_tenant_db_session)
):
    return tax_engine_service.actualizar_regla(db, x_entity_id, regla_id, payload)


# ==========================================
# SIMULADOR Y EXPORTADOR
# ==========================================
@router.post("/simular-retencion", response_model=SimularRetencionResponse)
def simular_retencion_multiple(
    payload: SimularRetencionRequest,
    x_entity_id: Annotated[int, Header()],
    db: Session = Depends(get_tenant_db_session)
):
    proveedor = db.query(ContactoComercial).filter(
        ContactoComercial.id == payload.proveedor_id,
        ContactoComercial.entidad_id == x_entity_id,
        ContactoComercial.is_active == True
    ).first()

    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor inactivo o no encontrado.")

    impuestos_calculados = tax_engine_service.evaluar_retenciones(
        db=db, entidad_id=x_entity_id, cuit_sujeto=proveedor.cuit,
        monto_base=payload.monto_bruto_abonar, fecha_operacion=date.today()
    )

    retenciones_sugeridas = []
    total_retenciones = Decimal('0.0')

    for imp in impuestos_calculados:
        retenciones_sugeridas.append(RetencionDetalleResponse(
            tipo_impuesto=imp.tipo_impuesto, jurisdiccion=imp.jurisdiccion,
            alicuota_aplicada=imp.alicuota_aplicada, monto_impuesto=imp.monto_impuesto
        ))
        total_retenciones += imp.monto_impuesto

    return SimularRetencionResponse(
        monto_bruto=payload.monto_bruto_abonar, retenciones_sugeridas=retenciones_sugeridas,
        total_retenciones=total_retenciones, neto_a_transferir=payload.monto_bruto_abonar - total_retenciones
    )

@router.get("/export/sire")
def export_sire_txt(
    x_entity_id: Annotated[int, Header()],
    periodo_fiscal: str = Query(..., description="YYYYMM (Ej: 202604)"),
    jurisdiccion: str = Query("AFIP"),
    clase_tributo: str = Query("RETENCION_EMITIDA"),
    db: Session = Depends(get_tenant_db_session),
    current_user: CachedUser = Depends(get_current_user)
):
    if getattr(current_user, "role", None) not in ["admin", "dueño", "operador"]:
        raise HTTPException(status_code=403, detail="Sin permisos para exportar datos.")

    try:
        registros_db = db.query(RegistroTributario).filter(
            RegistroTributario.entidad_id == x_entity_id,
            RegistroTributario.periodo_fiscal == periodo_fiscal,
            RegistroTributario.jurisdiccion == jurisdiccion,
            RegistroTributario.clase_tributo == clase_tributo,
            RegistroTributario.is_active == True
        ).all()

        if not registros_db:
            raise HTTPException(status_code=404, detail=f"No hay {clase_tributo} en {periodo_fiscal}.")

        lineas_sire = []
        for reg in registros_db:
            # 🌟 FIX LINEAGE: Extraemos dinámicamente el Tipo de Comprobante Real (Factura A, C, M, etc.)
            tipo_cbte_real = "001" # Default Factura A
            if reg.comprobante_id:
                cbte_original = db.query(Comprobante).filter(Comprobante.id == reg.comprobante_id).first()
                if cbte_original and getattr(cbte_original, 'tipo_cbte_afip', None):
                    tipo_cbte_real = str(cbte_original.tipo_cbte_afip).zfill(3)

            codigo_regimen = getattr(reg, '_codigo_regimen_dinamico', 217)

            linea = LineaExportacionSIRE(
                tipo_registro=1,
                fecha_retencion=reg.fecha_registro.strftime("%d/%m/%Y"),
                tipo_comprobante_origen=tipo_cbte_real,
                numero_comprobante_origen=(reg.numero_comprobante_origen or "0000000000000000").replace("-", "").replace(" ", "")[-16:],
                monto_comprobante_origen=reg.base_imponible + reg.monto_impuesto,
                codigo_regimen=codigo_regimen,
                cuit_sujeto_retenido=reg.cuit_sujeto.replace("-", ""),
                base_imponible=reg.base_imponible,
                monto_retencion=reg.monto_impuesto,
                numero_certificado=reg.numero_certificado.replace("-", "") if reg.numero_certificado else "0"
            )
            lineas_sire.append(linea)

        contenido_txt = FixedWidthFileGenerator.generate(lineas_sire)
        filename = f"SIRE_{jurisdiccion}_{periodo_fiscal}.txt"

        return Response(content=contenido_txt, media_type="text/plain", headers={"Content-Disposition": f"attachment; filename={filename}"})

    except Exception as e:
        logger.error(f"Fallo en SIRE: {e}")
        raise HTTPException(status_code=500, detail="Fallo compilando archivo posicional.")