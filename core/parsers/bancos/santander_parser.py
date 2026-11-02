import pandas as pd
from typing import Iterator
from decimal import Decimal
from core.parsers.interfaces import BaseParser
from core.schemas.ingest_models import StandardMovement, parse_monto_seguro

class SantanderCSVParser(BaseParser[StandardMovement]):
    def validate_format(self, file_path: str) -> None:
        try:
            cabeceras = pd.read_csv(file_path, sep=';', encoding='latin1', skiprows=3, nrows=0).columns.tolist()
            if not {'Fecha', 'Concepto', 'Importe'}.issubset(set(cabeceras)):
                raise ValueError("Columnas estándar del Banco Santander no encontradas.")
        except Exception as e:
            raise ValueError(f"Archivo ilegible o formato Santander inválido: {e}")

    def parse_generator(self, file_path: str) -> Iterator[StandardMovement]:
        for chunk in pd.read_csv(file_path, sep=';', encoding='latin1', skiprows=3, skip_blank_lines=True, chunksize=1000):
            for _, row in chunk.iterrows():
                if pd.isna(row.get('Fecha')): continue
                monto = parse_monto_seguro(row.get('Importe'))
                if monto == Decimal('0.00'): continue

                yield StandardMovement(
                    fecha=row['Fecha'],
                    concepto=str(row.get('Concepto', 'Sin concepto')),
                    monto=monto,
                    referencia_banco=str(row.get('Nro Comprobante', '')).strip()
                )