import logging
from decimal import Decimal
from typing import List
from pydantic import BaseModel

logger = logging.getLogger("TXT_EXPORTER")

class FixedWidthModel(BaseModel):
    """
    Clase base declarativa para la generación de archivos posicionales (TXT).
    Utiliza los metadatos de Pydantic V2 para calcular el ancho de cada columna.
    """

    def to_fixed_width_line(self) -> str:
        """
        Transforma los atributos del modelo en una línea de ancho fijo estricta.
        Lanza ValueError si algún dato excede el espacio asignado (Fail-Fast).
        """
        linea_componentes: List[str] = []

        # En Pydantic V2, model_fields conserva el orden exacto de declaración
        for nombre_campo, field_info in self.model_fields.items():
            valor = getattr(self, nombre_campo)

            # Extraer metadatos de configuración posicional
            extra = field_info.json_schema_extra or {}
            width = extra.get("width")
            padding_char = extra.get("padding", " ")
            alignment = extra.get("alignment", "<") # "<" izquierda, ">" derecha

            if width is None:
                raise ValueError(f"Configuración incompleta: El campo '{nombre_campo}' no define su ancho ('width').")

            # Formatear el valor según su tipo de dato original
            if isinstance(valor, Decimal) or isinstance(valor, float):
                # Formato fiscal estándar: sin comas ni puntos decimales (Ej: 150.45 -> "15045")
                valor_str = str(int(round(valor * 100)))
            elif isinstance(valor, int):
                valor_str = str(valor)
            elif valor is None:
                valor_str = ""
            else:
                valor_str = str(valor)

            # Validación Fail-Fast: Si el dato supera el ancho, interrumpe el proceso para evitar desfasar columnas
            if len(valor_str) > width:
                raise ValueError(
                    f"Fallo de Ingesta/Exportación: El valor '{valor_str}' en el campo '{nombre_campo}' "
                    f"supera el ancho máximo permitido de {width} caracteres."
                )

            # Aplicar el alineamiento y el relleno correspondiente
            if alignment == ">":
                componente_formateado = valor_str.rjust(width, padding_char)
            else:
                componente_formateado = valor_str.ljust(width, padding_char)

            linea_componentes.append(componente_formateado)

        return "".join(linea_componentes)


class FixedWidthFileGenerator:
    """
    Orquestador encargado de compilar colecciones de modelos posicionales
    en un bloque de texto listo para ser exportado como archivo .TXT.
    """
    @staticmethod
    def generate(records: List[FixedWidthModel]) -> str:
        if not records:
            return ""

        lineas = [record.to_fixed_width_line() for record in records]
        # Asegura finales de línea estilo Windows (CRLF) requeridos por los aplicativos SIAp
        return "\r\n".join(lineas) + "\r\n"