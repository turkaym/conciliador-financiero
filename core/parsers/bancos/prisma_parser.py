import csv
import io
import logging
import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Iterator

logger = logging.getLogger("PRISMA_PARSER")

class ParsedMovement:
    """DTO Efímero para tránsito en RAM"""
    def __init__(self, fecha, concepto, monto, referencia):
        self.fecha = fecha
        self.concepto = concepto
        self.monto = Decimal(str(monto))
        self.referencia_banco = referencia
        self.saldo_resultante = None
        self.ocurrencia_diaria = 1
        self.hash_transaccional = ""

    def generar_huella_criptografica(self):
        # Hash determinista para evitar duplicados exactos
        raw = f"{self.fecha}_{self.concepto.upper()}_{self.monto:.2f}_{self.ocurrencia_diaria}"
        self.hash_transaccional = hashlib.sha256(raw.encode('utf-8')).hexdigest()


class PrismaParser_v1:
    """
    Clearing Sintético Enterprise.
    Convierte 1 Fila de Liquidación Neta en 3 Movimientos Brutos Atómicos.
    Memoria O(1) vía Generators.
    """
    def __init__(self, column_mapping=None, **kwargs):
        self.mapping = column_mapping or {
            'fecha': 0, 'referencia': 1, 'bruto': 2, 'comision': 3, 'retenciones': 4, 'neto': 5
        }

    def parse_generator(self, file_stream) -> Iterator[ParsedMovement]:
        # 🌟 FIX ENTERPRISE: Bypass de TextIOWrapper.
        # Decodificamos el stream binario de urllib3 (MinIO) al vuelo (Lazy Evaluation).
        # Esto evita que el buffer de red se rompa al alcanzar el EOF abruptamente.
        decoded_stream = (line.decode('utf-8', errors='replace') for line in file_stream)
        reader = csv.reader(decoded_stream, delimiter=';')

        next(reader, None) # Saltar cabecera

        for row in reader:
            if not row or len(row) < 5:
                continue

            try:
                # 1. Extracción Cruda
                raw_fecha = row[self.mapping['fecha']].strip()
                fecha_obj = datetime.strptime(raw_fecha, "%d/%m/%Y").date()
                ref = row[self.mapping['referencia']].strip()

                bruto = Decimal(row[self.mapping['bruto']].replace(',', '.'))
                comision = Decimal(row[self.mapping['comision']].replace(',', '.'))
                retencion = Decimal(row[self.mapping['retenciones']].replace(',', '.'))

                # 2. Desempaquetado (Explosión de 1 a N)

                # A. Ingreso Bruto (Mata la factura impaga)
                if bruto > 0:
                    mov_bruto = ParsedMovement(
                        fecha=fecha_obj,
                        concepto=f"LIQUIDACION VENTA {ref}",
                        monto=bruto,
                        referencia=ref
                    )
                    yield mov_bruto

                # B. Egreso Operativo (Comisión de Tarjeta)
                if comision > 0:
                    mov_com = ParsedMovement(
                        fecha=fecha_obj,
                        concepto=f"COMISION PRISMA {ref}",
                        monto=-comision, # Negativo para salida
                        referencia=ref
                    )
                    yield mov_com

                # C. Egreso Impositivo (Retenciones)
                if retencion > 0:
                    mov_ret = ParsedMovement(
                        fecha=fecha_obj,
                        concepto=f"RETENCION IMPOSITIVA PRISMA {ref}",
                        monto=-retencion, # Negativo para salida
                        referencia=ref
                    )
                    yield mov_ret

            except Exception as e:
                logger.warning(f"Fila ignorada por formato inválido en Prisma: {row}. Error: {e}")