from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Union
from pydantic import BaseModel

from core.matching.reports import get_matched_history, get_unreconciled_data, _format_cbte
from core.database.session import get_tenant_db
from core.database.models_tenant import ConciliacionMatch, RazonSocialPropia, Comprobante
from core.api.deps import get_current_user

from core.matching.engine import run_advanced_matching
from core.matching.transactions import force_manual_match, ejecutar_reversion_segura
from core.tasks.maintenance_tasks import run_tenant_matching_task

router = APIRouter(tags=["Conciliación"])

class ManualMatchRequest(BaseModel):
    comprobantes_ids: List[Union[str, int]]
    movimientos_ids: List[int]
    ajustes_fiscales: list = [] # Opcional Fase C

@router.get("/status/{schema_name}")
def get_reconciliation_status(
    schema_name: str,
    entidad_id: int = Query(..., description="ID de la entidad/empresa a consultar"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user)
):
    if current_user.tenant.schema_name != schema_name and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No tienes acceso a los datos de este tenant")

    db_gen = get_tenant_db(schema_name)
    db = next(db_gen)
    try:
        entidad = db.query(RazonSocialPropia).filter(RazonSocialPropia.id == entidad_id).first()
        if not entidad:
            raise HTTPException(status_code=404, detail="Entidad no existe")

        data = get_unreconciled_data(db, entidad_id=entidad.id, limit=limit, offset=offset)
        total_matches = db.query(ConciliacionMatch).filter(ConciliacionMatch.is_active == True).count()

        def serialize_cbtes(hibrido_list):
            resultados = []
            for item in hibrido_list:
                tipo = getattr(item, 'tipo_registro', 'COMPROBANTE')

                try:
                    num_fmt = _format_cbte(item)
                except Exception:
                    num_fmt = "S/R"

                # Discriminación polimórfica y asignación de ID híbrido (Modelo Ledger)
                if tipo == 'MOVIMIENTO_INTERNO':
                    fecha_str = item.fecha.strftime("%Y-%m-%d") if getattr(item, 'fecha', None) else None
                    razon_social = getattr(item, 'concepto_crudo', 'Movimiento Interno')
                    moneda = str(getattr(item.cuenta.moneda, 'value', item.cuenta.moneda)) if getattr(item, 'cuenta', None) and getattr(item.cuenta, 'moneda', None) else "ARS"
                    item_id = f"MOV-{item.id}"
                else:
                    fecha_str = item.fecha_emision.strftime("%Y-%m-%d") if getattr(item, 'fecha_emision', None) else None
                    razon_social = getattr(item, 'razon_social_receptor', None) or getattr(item, 'cuit_emisor', 'S/D')
                    moneda = str(getattr(item.moneda, 'value', item.moneda)) if getattr(item, 'moneda', None) else "ARS"
                    item_id = f"CBT-{item.id}" if tipo != 'ORDEN_PAGO' else f"OP-{item.id}"

                resultados.append({
                    "id": item_id,
                    "numero_formateado": num_fmt,
                    "fecha": fecha_str,
                    "razon_social": razon_social,
                    "monto": float(item.saldo_pendiente),
                    "moneda": moneda,
                    "clase_documento": getattr(item, 'clase_documento', None)
                })
            return resultados

        def serialize_movs(movs_list):
            return [
                {
                    "id": m.id,
                    "fecha": m.fecha.strftime("%Y-%m-%d") if getattr(m, 'fecha', None) else None,
                    "concepto": m.concepto_crudo,
                    "referencia": m.referencia_externa or "S/R",
                    "monto": float(m.monto),
                    "moneda": str(getattr(m.cuenta.moneda, 'value', m.cuenta.moneda)) if getattr(m, 'cuenta', None) and getattr(m.cuenta, 'moneda', None) else "ARS"
                } for m in movs_list
            ]

        return {
            "tenant": schema_name,
            "entidad_id": entidad.id,
            "summary": {
                "matched_count": total_matches,
                "ar_pending": data["ar_cbtes_count"] + data["ar_movs_count"],
                "ap_pending": data["ap_cbtes_count"] + data["ap_movs_count"]
            },
            "pendings": {
                "ar": {
                    "invoices": serialize_cbtes(data["ar_cbtes"]),
                    "bank_movements": serialize_movs(data["ar_movs"])
                },
                "ap": {
                    "invoices": serialize_cbtes(data["ap_cbtes"]),
                    "bank_movements": serialize_movs(data["ap_movs"])
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {str(e)}")
    finally:
        db.close()

@router.post("/run/{schema_name}")
def trigger_matching(
    schema_name: str,
    entidad_id: int = Query(...),
    current_user = Depends(get_current_user)
):
    if current_user.tenant.schema_name != schema_name and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos")

    db_gen = get_tenant_db(schema_name)
    db = next(db_gen)
    try:
        entidad = db.query(RazonSocialPropia).filter(RazonSocialPropia.id == entidad_id).first()
        if not entidad:
            raise HTTPException(status_code=404, detail="Entidad no existe.")

        cantidad_pendientes = db.query(Comprobante).filter(
            Comprobante.entidad_id == entidad_id,
            Comprobante.estado.in_(["PENDIENTE", "PARCIALMENTE CONCILIADO"]),
            Comprobante.saldo_pendiente > 0
        ).count()

        if cantidad_pendientes > 100:
            tarea = run_tenant_matching_task.apply_async(
                kwargs={"tenant_id": schema_name, "entidad_id": entidad.id},
                queue='matching_queue'
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "status": "processing_async",
                    "message": "Alto volumen. Background process iniciado.",
                    "task_id": tarea.id,
                    "estimated_pending": cantidad_pendientes
                }
            )

        new_matches = run_advanced_matching(db, schema_name, entidad_id=entidad.id)
        return {"status": "success", "new_matches_found": new_matches}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Motor fail: {str(e)}")
    finally:
        db.close()

@router.post("/manual-match/{schema_name}")
def manual_match(
    schema_name: str,
    request: ManualMatchRequest,
    current_user = Depends(get_current_user)
):
    if current_user.tenant.schema_name != schema_name and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos")

    if not request.comprobantes_ids or not request.movimientos_ids:
        raise HTTPException(status_code=400, detail="Faltan Ids")

    # 🌟 FIX POLIMORFISMO: Desempaquetado estricto
    cbtes_reales_ids = []
    op_reales_ids = []
    for cid in request.comprobantes_ids:
        cid_str = str(cid)
        if cid_str.startswith("CBT-"):
            cbtes_reales_ids.append(int(cid_str.replace("CBT-", "")))
        elif cid_str.startswith("OP-"):
            op_reales_ids.append(int(cid_str.replace("OP-", "")))
        elif cid_str.isdigit():
            cbtes_reales_ids.append(int(cid_str))

    db_gen = get_tenant_db(schema_name)
    db = next(db_gen)
    try:
        exito = force_manual_match(
            db=db,
            tenant_id=schema_name,
            comprobantes_ids=cbtes_reales_ids,
            movimientos_ids=request.movimientos_ids,
            usuario_id=current_user.sub,
            ajustes_fiscales=request.ajustes_fiscales,
            op_ids=op_reales_ids
        )

        if not exito:
            raise HTTPException(status_code=400, detail="Match no concretado. Verifique saldos u operaciones concurrentes.")

        return {"status": "match_manual_registrado", "aprendizaje_disparado": True, "asiento_en_proceso": True}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/unmatch/{schema_name}")
def unmatch_records(
    schema_name: str,
    match_id: int = Query(...),
    current_user = Depends(get_current_user)
):
    if current_user.tenant.schema_name != schema_name and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos")

    db_gen = get_tenant_db(schema_name)
    db = next(db_gen)
    try:
        reversion_exitosa = ejecutar_reversion_segura(db, schema_name, match_id)
        if not reversion_exitosa:
            raise HTTPException(status_code=404, detail="Match no encontrado.")
        return {"status": "unmatched_successfully", "reversal_triggered": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/history/{schema_name}")
def get_reconciliation_history(
    schema_name: str,
    entidad_id: int = Query(...),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user)
):
    if current_user.tenant.schema_name != schema_name and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos")

    db_gen = get_tenant_db(schema_name)
    db = next(db_gen)
    try:
        return get_matched_history(db, entidad_id, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()