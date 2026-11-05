import re
import unicodedata
import logging
from typing import Any

logger = logging.getLogger("ADUANA_DATOS")

# Diccionario estricto de equivalencias hacia el estándar ISO 4217
MAPA_DIVISAS_ISO = {
    # Peso Argentino
    "PES": "ARS", "PESOS": "ARS", "$": "ARS", "AR$": "ARS", "ARG": "ARS", "ARS": "ARS",
    # Dólar Estadounidense
    "DOLAR": "USD", "US$": "USD", "U$S": "USD", "DOL": "USD", "USD": "USD",
    # Euro
    "EUROS": "EUR", "€": "EUR", "EUR": "EUR"
}

def sanitize_string(text: Any) -> str:
    """
    Sanitizador Extremo.
    Elimina caracteres invisibles (Zero-width spaces), normaliza acentos a ASCII puro
    y colapsa espacios múltiples.
    """
    if text is None or str(text).strip() == "":
        return ""

    text_str = str(text)
    # 1. Eliminar caracteres Unicode invisibles (Bugs clásicos de exportaciones bancarias Excel)
    text_str = re.sub(r'[\u200B-\u200D\uFEFF]', '', text_str)

    # 2. Normalizar acentos (Ej: "Crédito" -> "Credito")
    text_str = unicodedata.normalize('NFKD', text_str).encode('ASCII', 'ignore').decode('utf-8')

    # 3. Limpiar espacios redundantes (Trim interno y externo)
    text_str = " ".join(text_str.split())

    return text_str

def normalizar_moneda(valor_crudo: Any) -> str:
    """
    Intercepta cualquier denominación de moneda y la traduce forzosamente a ISO 4217.
    """
    if not valor_crudo:
        return "ARS"

    valor_limpio = sanitize_string(valor_crudo).upper()

    if valor_limpio in MAPA_DIVISAS_ISO:
        moneda_normalizada = MAPA_DIVISAS_ISO[valor_limpio]
        return moneda_normalizada

    return valor_limpio

def normalizar_cuit(cuit_crudo: Any) -> str:
    """
    Aduana Central de CUITs.
    Destruye cualquier formato humano y conserva exclusivamente los 11 dígitos numéricos.
    """
    if not cuit_crudo:
        return ""
    # Mantiene exclusivamente números, matando guiones, puntos o letras.
    return re.sub(r'\D', '', str(cuit_crudo))