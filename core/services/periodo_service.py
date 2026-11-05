from datetime import date
from sqlalchemy.orm import Session
from core.database.models_tenant import PeriodoContable

class PeriodoService:
    """
    Servicio transversal para validación de bloqueos temporales contables.
    Actúa como escudo protector antes de cualquier mutación de datos.
    """

    def validar_fecha_operacion(self, db: Session, fecha: date):
        """
        Verifica si la fecha de la operación cae en un período bloqueado.
        Lanza ValueError si el período está cerrado.
        """
        return self.verificar_periodo_abierto(db, fecha.year, fecha.month)

    def verificar_periodo_abierto(self, db: Session, anio: int, mes: int):
        """
        🛡️ BLINDAJE CORE: Lanzamos ValueError (nativo de Python) para que
        tanto FastAPI como Celery puedan capturarlo sin romper su contexto.
        """
        periodo = db.query(PeriodoContable).filter_by(anio=anio, mes=mes).first()

        if periodo and periodo.estado == "CERRADO":
            raise ValueError(
                f"🔒 Operación denegada: El período contable de {mes}/{anio} se encuentra CERRADO. No se pueden alterar datos históricos."
            )
        return True

    def cerrar_periodo(self, db: Session, anio: int, mes: int, usuario_id: int):
        """Sella un mes contable para evitar modificaciones futuras."""
        periodo = db.query(PeriodoContable).filter_by(anio=anio, mes=mes).first()

        if periodo and periodo.estado == "CERRADO":
            raise ValueError(f"El período {mes}/{anio} ya se encuentra cerrado.")

        if not periodo:
            periodo = PeriodoContable(
                anio=anio,
                mes=mes,
                estado="CERRADO",
                cerrado_por_id=usuario_id
            )
            db.add(periodo)
        else:
            periodo.estado = "CERRADO"
            periodo.cerrado_por_id = usuario_id

        db.commit()
        db.refresh(periodo)
        return periodo

    def obtener_periodos(self, db: Session):
        """Lista los periodos para que el Frontend sepa cuáles bloquear en la UI."""
        return db.query(PeriodoContable).order_by(PeriodoContable.anio.desc(), PeriodoContable.mes.desc()).all()

# 🌟 FIX RIESGO DE IMPORTACIÓN:
# Instanciamos la clase aquí para que todo el sistema use el mismo objeto en memoria
periodo_service = PeriodoService()