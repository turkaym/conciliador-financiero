import csv
import io
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("HEURISTIC_ENGINE")

class HeuristicEngine:
    """Motor X-Ray para inferencia de formatos bancarios desconocidos."""

    # Diccionario de reconocimiento probabilístico
    PATTERNS = {
        "fecha": [
            re.compile(r'^\d{2}/\d{2}/\d{4}$'),        # 31/12/2026
            re.compile(r'^\d{4}-\d{2}-\d{2}$'),        # 2026-12-31
            re.compile(r'^\d{2}-\d{2}-\d{4}$'),        # 31-12-2026
        ],
        "monto": [
            re.compile(r'^-?\d{1,3}(?:\.\d{3})*,\d{2}$'), # -1.500,00 (AR)
            re.compile(r'^-?\d{1,3}(?:,\d{3})*\.\d{2}$'), # -1,500.00 (US)
            re.compile(r'^-?\d+,\d{2}$'),                 # -1500,00
            re.compile(r'^-?\d+\.\d{2}$'),                # -1500.00
        ],
        "referencia": [
            re.compile(r'^\d{6,22}$'),                 # Numéricos largos
            re.compile(r'^[A-Z0-9]{8,15}$'),           # Alfanuméricos transaccionales
        ]
    }

    @classmethod
    def analyze_sample(cls, file_stream: bytes, extension: str) -> Dict[str, Any]:
        """
        Analiza una muestra de bytes y devuelve el esquema inferido.
        """
        ext = extension.lower()
        if ext in ['.csv', '.txt']:
            return cls._analyze_csv_sample(file_stream)
        elif ext in ['.xlsx', '.xls']:
            return cls._analyze_excel_sample(file_stream)
        else:
            raise ValueError(f"Formato no soportado para análisis heurístico: {ext}")

    @classmethod
    def _analyze_csv_sample(cls, file_stream: bytes) -> Dict[str, Any]:
        try:
            # Decodificamos de forma segura ignorando errores en el chunk
            content = file_stream.decode('utf-8', errors='ignore')
        except Exception:
            content = file_stream.decode('latin-1', errors='ignore')

        # 🌟 FIX X-RAY: Evaluación competitiva de delimitadores
        # Probamos con Punto y Coma
        reader_sc = csv.reader(io.StringIO(content), delimiter=';')
        lineas_sc = list(reader_sc)
        max_cols_sc = max([len(row) for row in lineas_sc if row] + [0])

        # Probamos con Coma
        reader_c = csv.reader(io.StringIO(content), delimiter=',')
        lineas_c = list(reader_c)
        max_cols_c = max([len(row) for row in lineas_c if row] + [0])

        # Gana el delimitador que haya logrado estructurar más columnas
        if max_cols_c > max_cols_sc:
            lineas_brutas = lineas_c
        else:
            lineas_brutas = lineas_sc

        return cls._infer_schema(lineas_brutas)

    @classmethod
    def _analyze_excel_sample(cls, file_stream: bytes) -> Dict[str, Any]:
        import openpyxl
        # Openpyxl puede leer desde un buffer de bytes en RAM
        wb = openpyxl.load_workbook(io.BytesIO(file_stream), read_only=True, data_only=True)
        sheet = wb.active

        lineas_brutas = []
        for row in sheet.iter_rows(min_row=1, max_row=30, values_only=True):
            # Convertimos todo a string para el motor RegEx
            lineas_brutas.append([str(cell) if cell is not None else "" for cell in row])

        wb.close()
        return cls._infer_schema(lineas_brutas)

    @classmethod
    def _infer_schema(cls, rows: List[List[str]]) -> Dict[str, Any]:
        """El corazón matemático del Motor X-Ray."""
        if not rows:
            return {"status": "error", "message": "Archivo vacío."}

        # 1. Limpieza de Cabecera: Buscamos la primera fila que tenga datos densos
        # Los bancos suelen poner logos o texto inútil en las primeras 5 líneas
        data_start_idx = 0
        max_cols = 0
        for i, row in enumerate(rows[:10]):
            cols_con_datos = sum(1 for cell in row if str(cell).strip())
            if cols_con_datos > max_cols:
                max_cols = cols_con_datos
                data_start_idx = i

        # Extraemos las cabeceras supuestas y las filas de datos reales
        headers = rows[data_start_idx]
        data_sample = rows[data_start_idx + 1: data_start_idx + 11]

        # 2. Puntuación (Scoring): Evaluamos cada columna
        inferred_mapping = {}
        column_analysis = []

        for col_idx in range(len(headers)):
            col_name = str(headers[col_idx]).strip() if col_idx < len(headers) else f"Columna_{col_idx}"
            scores = {"fecha": 0, "monto": 0, "referencia": 0, "concepto": 0}

            muestras_validas = 0
            for row in data_sample:
                if col_idx < len(row):
                    cell_val = str(row[col_idx]).strip()
                    if not cell_val: continue

                    muestras_validas += 1

                    # Test RegEx
                    if any(p.match(cell_val) for p in cls.PATTERNS["fecha"]): scores["fecha"] += 1
                    elif any(p.match(cell_val) for p in cls.PATTERNS["monto"]): scores["monto"] += 1
                    elif any(p.match(cell_val) for p in cls.PATTERNS["referencia"]): scores["referencia"] += 1
                    elif len(cell_val) > 10 and not cell_val.isnumeric(): scores["concepto"] += 1

            # Determinamos el ganador si supera un umbral de confianza (ej. 50%)
            tipo_ganador = "desconocido"
            if muestras_validas > 0:
                for tipo, puntaje in scores.items():
                    if puntaje / muestras_validas >= 0.5:
                        tipo_ganador = tipo
                        break

            column_analysis.append({
                "index": col_idx,
                "header": col_name,
                "inferred_type": tipo_ganador,
                "sample_values": [str(r[col_idx]).strip() for r in data_sample if col_idx < len(r)][:3]
            })

            if tipo_ganador != "desconocido" and tipo_ganador not in inferred_mapping:
                inferred_mapping[tipo_ganador] = col_idx

        return {
            "status": "success",
            "start_row": data_start_idx + 1,
            "inferred_mapping": inferred_mapping,
            "columns": column_analysis
        }