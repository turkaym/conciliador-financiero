import openpyxl
import pandas as pd
from typing import Iterator
from decimal import Decimal
from core.parsers.interfaces import BaseParser
from core.schemas.ingest_models import StandardMovement, parse_monto_seguro

class GaliciaExcelParser(BaseParser[StandardMovement]):
    def validate_format(self, file_path: str) -> None:
        try:
            cabeceras = pd.read_excel(file_path, skiprows=1, nrows=0, engine='openpyxl').columns.tolist()
            if not {'Fecha', 'Descripción', 'Importe'}.issubset(set(cabeceras)):
                raise ValueError("Columnas estándar del Banco Galicia no encontradas.")
        except Exception as e:
            raise ValueError(f"Archivo ilegible o formato Galicia inválido: {e}")

    def parse_generator(self, file_path: str) -> Iterator[StandardMovement]:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active

        headers = {str(val).strip(): idx for idx, val in enumerate(next(ws.iter_rows(min_row=2, max_row=2, values_only=True))) if val}
        if 'Fecha' not in headers or 'Importe' not in headers:
            wb.close()
            return

        idx_fecha, idx_desc = headers['Fecha'], headers.get('Descripción', -1)
        idx_importe, idx_saldo = headers['Importe'], headers.get('Saldo', -1)

        for row in ws.iter_rows(min_row=3, values_only=True):
            if not row[idx_fecha]: continue

            monto = parse_monto_seguro(row[idx_importe])
            if monto == Decimal('0.00'): continue

            yield StandardMovement(
                fecha=row[idx_fecha],
                concepto=str(row[idx_desc]) if idx_desc != -1 and row[idx_desc] else 'Sin concepto',
                monto=monto,
                saldo_resultante=parse_monto_seguro(row[idx_saldo]) if idx_saldo != -1 else None
            )
        wb.close()