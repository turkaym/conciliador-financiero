from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date

from core.database.session import get_tenant_db
from core.database.models_tenant import PlanCuentas, AsientoContable, LineaAsiento
from core.api.deps import get_current_user, CachedUser

router = APIRouter(tags=["Reportes Contables"])

@router.get("/ledger/{schema_name}")
def get_general_ledger(
    schema_name: str,
    cuenta_codigo: str = Query(..., description="Código de la cuenta contable (ej. 1.1.01.02)"),
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    current_user: CachedUser = Depends(get_current_user)
):
    """Obtiene el Libro Mayor respetando la naturaleza Deudora o Acreedora de la cuenta."""
    # FIX: Acceso correcto a las propiedades del objeto CachedUser
    if getattr(current_user, "tenant_id", None) != schema_name and getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos para este tenant")

    db_gen = get_tenant_db(schema_name)
    db = next(db_gen)

    try:
        cuenta = db.query(PlanCuentas).filter(PlanCuentas.codigo == cuenta_codigo).first()
        if not cuenta:
            raise HTTPException(status_code=404, detail=f"Cuenta {cuenta_codigo} no encontrada")

        # FIX CONTABLE: Multiplicador según naturaleza de la cuenta
        tipo_upper = cuenta.tipo.upper()
        es_acreedora = tipo_upper in ["PASIVO", "PATRIMONIO", "RESULTADO POSITIVO", "INGRESO"]
        multiplicador = -1 if es_acreedora else 1

        # Calcular Saldo Inicial
        saldo_inicial = 0.0
        if fecha_desde:
            resultado_inicial = db.query(
                func.sum((LineaAsiento.debe - LineaAsiento.haber) * multiplicador)
            ).join(
                AsientoContable, AsientoContable.id == LineaAsiento.asiento_id
            ).filter(
                LineaAsiento.cuenta_id == cuenta.id,
                AsientoContable.fecha < fecha_desde
            ).scalar()
            saldo_inicial = float(resultado_inicial or 0.0)

        # Consulta de Movimientos
        query = db.query(
            AsientoContable.fecha,
            AsientoContable.id.label('asiento_id'),
            AsientoContable.concepto,
            LineaAsiento.debe,
            LineaAsiento.haber
        ).join(
            LineaAsiento, AsientoContable.id == LineaAsiento.asiento_id
        ).filter(
            LineaAsiento.cuenta_id == cuenta.id
        )

        if fecha_desde:
            query = query.filter(AsientoContable.fecha >= fecha_desde)
        if fecha_hasta:
            query = query.filter(AsientoContable.fecha <= fecha_hasta)

        query = query.order_by(AsientoContable.fecha, AsientoContable.id)
        resultados = query.all()

        # Acumular saldo real
        movimientos = []
        saldo_acumulado = saldo_inicial

        for row in resultados:
            flujo_renglon = float((row.debe - row.haber) * multiplicador)
            saldo_acumulado += flujo_renglon

            movimientos.append({
                "fecha": row.fecha,
                "asiento_id": row.asiento_id,
                "concepto": row.concepto,
                "debe": float(row.debe),
                "haber": float(row.haber),
                "saldo": float(saldo_acumulado)
            })

        return {
            "tenant": schema_name,
            "cuenta": {
                "codigo": cuenta.codigo,
                "nombre": cuenta.nombre,
                "tipo": cuenta.tipo,
                "naturaleza": "Acreedora" if es_acreedora else "Deudora"
            },
            "saldo_inicial_periodo": saldo_inicial,
            "total_movimientos": len(movimientos),
            "saldo_actual": saldo_acumulado,
            "movimientos": movimientos
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar Libro Mayor: {str(e)}")
    finally:
        db.close()

@router.get("/trial-balance/{schema_name}")
def get_trial_balance(
    schema_name: str,
    fecha_hasta: Optional[date] = None,
    current_user: CachedUser = Depends(get_current_user)
):
    """Balance de Sumas y Saldos a nivel Tenant."""
    # FIX: Acceso correcto a las propiedades del objeto CachedUser
    if getattr(current_user, "tenant_id", None) != schema_name and getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos para este tenant")

    db_gen = get_tenant_db(schema_name)
    db = next(db_gen)

    try:
        join_conditions = [LineaAsiento.cuenta_id == PlanCuentas.id]

        query = db.query(
            PlanCuentas.codigo,
            PlanCuentas.nombre,
            PlanCuentas.tipo,
            func.coalesce(func.sum(LineaAsiento.debe), 0).label('total_debe'),
            func.coalesce(func.sum(LineaAsiento.haber), 0).label('total_haber')
        ).outerjoin(
            LineaAsiento, *join_conditions
        ).outerjoin(
            AsientoContable, LineaAsiento.asiento_id == AsientoContable.id
        )

        if fecha_hasta:
            query = query.filter(AsientoContable.fecha <= fecha_hasta)

        query = query.group_by(
            PlanCuentas.id, PlanCuentas.codigo, PlanCuentas.nombre, PlanCuentas.tipo
        ).order_by(PlanCuentas.codigo)

        resultados = query.all()

        balance = []
        suma_debe_total = 0.0
        suma_haber_total = 0.0

        for row in resultados:
            debe = float(row.total_debe)
            haber = float(row.total_haber)

            if debe > 0 or haber > 0:
                suma_debe_total += debe
                suma_haber_total += haber

                balance.append({
                    "codigo": row.codigo,
                    "nombre": row.nombre,
                    "tipo": row.tipo,
                    "sumas": {
                        "debe": debe,
                        "haber": haber
                    },
                    "saldos": {
                        "deudor": debe - haber if debe > haber else 0,
                        "acreedor": haber - debe if haber > debe else 0
                    }
                })

        return {
            "tenant": schema_name,
            "fecha_corte": fecha_hasta or "Actual",
            "cuentas_activas": len(balance),
            "totales": {
                "sumas_debe": suma_debe_total,
                "sumas_haber": suma_haber_total,
                "balance_cuadrado": round(suma_debe_total, 2) == round(suma_haber_total, 2)
            },
            "balance": balance
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar Sumas y Saldos: {str(e)}")
    finally:
        db.close()