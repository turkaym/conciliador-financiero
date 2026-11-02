import pandas as pd
from typing import Iterator
from decimal import Decimal
from core.parsers.interfaces import BaseParser
from core.schemas.ingest_models import StandardMovement, parse_monto_seguro

class MercadoPagoCSVParser(BaseParser[StandardMovement]):
    def validate_format(self, file_path: str) -> None:
        try:
            # MP usa separadores dinámicos (, o ;) dependiendo de la exportación
            cabeceras = pd.read_csv(file_path, sep=None, engine='python', nrows=0).columns.tolist()
            if not any(col in cabeceras for col in ['Fecha de creación', 'Monto', 'Neto recibido']):
                raise ValueError("Columnas estándar de Mercado Pago no encontradas.")
        except Exception as e:
            raise ValueError(f"Archivo ilegible o formato Mercado Pago inválido: {e}")

    def parse_generator(self, file_path: str) -> Iterator[StandardMovement]:
        for chunk in pd.read_csv(file_path, sep=None, engine='python', skip_blank_lines=True, chunksize=1000):
            for _, row in chunk.iterrows():
                if pd.isna(row.get('Fecha de creación')): continue

                # MP detalla "Neto recibido" (post comisiones) y "Monto" (bruto)
                monto_str = row.get('Neto recibido') if pd.notna(row.get('Neto recibido')) else row.get('Monto')
                monto = parse_monto_seguro(monto_str)
                if monto == Decimal('0.00'): continue

                yield StandardMovement(
                    fecha=row['Fecha de creación'],
                    concepto=str(row.get('Descripción', 'Sin detalle')),
                    monto=monto,
                    referencia_banco=str(row.get('Número de operación', '')).strip()
                )