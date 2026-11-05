import hashlib
import pandas as pd
from datetime import datetime, date
from typing import Optional
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, Field, field_validator

from core.utils.normalizer import normalizar_moneda

def parse_monto_seguro(valor_crudo) -> Decimal:
    """Convierte cualquier aberración de string bancario en un Decimal exacto."""
    if pd.isna(valor_crudo) or valor_crudo is None: return Decimal('0.00')
    try:
        if isinstance(valor_crudo, (int, float, Decimal)): return Decimal(str(valor_crudo))
        val_str = str(valor_crudo).strip().replace('$', '').replace('.', '').replace(',', '.')
        return Decimal(val_str)
    except (ValueError, InvalidOperation):
        return Decimal('0.00')

class StandardMovement(BaseModel):
    fecha: date
    concepto: str
    monto: Decimal
    referencia_banco: str = Field(default="")
    saldo_resultante: Optional[Decimal] = None
    moneda: str = Field(default="ARS")
    ocurrencia_diaria: int = 0
    hash_transaccional: str = Field(default="")

    @field_validator('fecha', mode='before')
    def parse_flexible_date(cls, v):
        if pd.isna(v) or v is None: raise ValueError("La fecha no puede estar vacía")
        if isinstance(v, date): return v
        if isinstance(v, pd.Timestamp): return v.date()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y%m%d"):
            try: return datetime.strptime(str(v).split()[0], fmt).date()
            except ValueError: continue
        raise ValueError(f"Formato de fecha desconocido: {v}")

    @field_validator('moneda', mode='before')
    def normalizar_divisa(cls, v):
        return normalizar_moneda(v)

    def generar_huella_criptografica(self):
        """Genera una firma SHA-256 inmutable, ignorando la referencia basura del banco."""
        raw_string = f"{self.fecha}|{self.concepto.strip().upper()}|{self.monto:.2f}|{self.ocurrencia_diaria}|{self.moneda}"
        self.hash_transaccional = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()
        return self