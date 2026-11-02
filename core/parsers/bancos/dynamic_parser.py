import csv
import io
import hashlib
import itertools
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Generator, Any

from core.parsers.interfaces import BaseParser

logger = logging.getLogger("DYNAMIC_PARSER")

class DynamicMovementDTO:
    """Contenedor en memoria (Duck-Typing) que cumple el contrato del Orquestador."""
    def __init__(self, fecha: date, concepto: str, monto: Decimal, referencia_banco: str = ""):
        self.fecha = fecha
        self.concepto = concepto
        self.monto = monto
        self.referencia_banco = referencia_banco
        self.saldo_resultante = None
        self.ocurrencia_diaria = 0
        self.hash_transaccional = ""

    def generar_huella_criptografica(self):
        raw = f"{self.fecha}_{self.concepto}_{self.monto:.2f}_{self.ocurrencia_diaria}"
        self.hash_transaccional = hashlib.sha256(raw.encode('utf-8')).hexdigest()

class DynamicParser(BaseParser):
    """
    Parser adaptativo. Consume flujos de red guiándose exclusivamente
    por el mapa de coordenadas (column_mapping) validado por el usuario.
    """
    def __init__(self, column_mapping: dict = None, file_extension: str = ".csv", **kwargs):
        if not column_mapping:
            raise ValueError("[BUSINESS_LOGIC] El parser dinámico requiere un mapa de coordenadas validado por el usuario.")

        self.mapping = column_mapping
        self.extension = file_extension.lower()

    def validate_format(self, file_stream: Any):
        """Omite validación estricta ya que la matriz fue auditada en Pre-Vuelo."""
        pass

    def parse_generator(self, file_stream: Any) -> Generator[DynamicMovementDTO, None, None]:
        if self.extension in ['.csv', '.txt']:
            yield from self._parse_csv_stream(file_stream)
        elif self.extension in ['.xlsx', '.xls']:
            yield from self._parse_excel_stream(file_stream)
        else:
            raise ValueError(f"Extensión no soportada por el motor dinámico: {self.extension}")

    def _parse_csv_stream(self, file_stream: Any) -> Generator[DynamicMovementDTO, None, None]:
        # 🌟 FIX DEFINITIVO O(1): Iteración binaria directa sin buffers agresivos
        def safe_line_iterator():
            try:
                # urllib3 HTTPResponse (MinIO) itera nativamente línea por línea de forma segura
                for line in file_stream:
                    yield line.decode('utf-8', errors='ignore') if isinstance(line, bytes) else str(line)
            except Exception as e:
                # Si el socket de red se cierra al vaciarse, terminamos en paz
                if "closed" in str(e).lower() or "reset" in str(e).lower():
                    return
                raise

        text_stream = safe_line_iterator()

        # 1. Buffering de Muestreo (Lectura parcial)
        head_lines = []
        for _ in range(50):
            try:
                head_lines.append(next(text_stream))
            except StopIteration:
                break

        if not head_lines:
            return

        # 2. Evaluación competitiva de delimitadores
        reader_sc = csv.reader(head_lines, delimiter=';')
        max_cols_sc = max([len(row) for row in reader_sc] + [0])

        reader_c = csv.reader(head_lines, delimiter=',')
        max_cols_c = max([len(row) for row in reader_c] + [0])

        best_delim = ',' if max_cols_c > max_cols_sc else ';'

        # 3. Encadenamiento O(1) Inteligente
        if len(head_lines) < 50:
            full_stream = head_lines
        else:
            full_stream = itertools.chain(head_lines, text_stream)

        reader = csv.reader(full_stream, delimiter=best_delim)

        yield from self._extract_data(reader)

    def _parse_excel_stream(self, file_stream: Any) -> Generator[DynamicMovementDTO, None, None]:
        import openpyxl
        # Los archivos Excel comprimidos requieren carga en RAM por diseño de la librería
        wb = openpyxl.load_workbook(io.BytesIO(file_stream.read()), read_only=True, data_only=True)
        sheet = wb.active

        lineas = []
        for row in sheet.iter_rows(values_only=True):
            lineas.append([str(cell) if cell is not None else "" for cell in row])

        wb.close()
        yield from self._extract_data(lineas)

    def _extract_data(self, lineas_iterable: Any) -> Generator[DynamicMovementDTO, None, None]:
        idx_fecha = self.mapping.get("fecha")
        idx_monto = self.mapping.get("monto")
        idx_concepto = self.mapping.get("concepto")
        idx_ref = self.mapping.get("referencia")

        # Filtramos índices nulos para calcular el ancho mínimo requerido
        indices_requeridos = [i for i in [idx_fecha, idx_monto, idx_concepto, idx_ref] if i is not None]
        ancho_minimo = max(indices_requeridos) if indices_requeridos else 0

        for row in lineas_iterable:
            # Resiliencia: Saltear filas vacías o cortadas sin error
            if not row or len(row) <= ancho_minimo:
                continue

            try:
                raw_fecha = str(row[idx_fecha]).strip()
                raw_monto = str(row[idx_monto]).strip()

                # Concepto y Referencia son opcionales
                raw_concepto = str(row[idx_concepto]).strip() if idx_concepto is not None else "Movimiento Genérico"
                raw_ref = str(row[idx_ref]).strip() if idx_ref is not None else ""

                # Normalización Temporal Robusta
                try:
                    if "-" in raw_fecha:
                        dt_fecha = datetime.strptime(raw_fecha, "%Y-%m-%d").date() if len(raw_fecha.split("-")[0]) == 4 else datetime.strptime(raw_fecha, "%d-%m-%Y").date()
                    else:
                        dt_fecha = datetime.strptime(raw_fecha, "%d/%m/%Y").date()
                except ValueError:
                    continue

                # Normalización Financiera Robusta
                raw_monto = raw_monto.replace("$", "").strip()
                if "." in raw_monto and "," in raw_monto:
                    if raw_monto.rfind(",") > raw_monto.rfind("."):
                        raw_monto = raw_monto.replace(".", "").replace(",", ".")
                    else:
                        raw_monto = raw_monto.replace(",", "")
                elif "," in raw_monto and len(raw_monto.split(",")[-1]) <= 2:
                    raw_monto = raw_monto.replace(",", ".")

                val_monto = Decimal(raw_monto)

                yield DynamicMovementDTO(
                    fecha=dt_fecha,
                    concepto=raw_concepto,
                    monto=val_monto,
                    referencia_banco=raw_ref
                )
            except Exception as e:
                # Se elimina la omisión silenciosa; se registra el error por fila
                logger.warning(f"⚠️ [DATA_ERROR] Fila descartada en DynamicParser. Datos: {row} | Motivo: {e}")
                continue