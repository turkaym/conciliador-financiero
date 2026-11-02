from enum import Enum

class BusinessErrorCode(str, Enum):
    # Errores de Ingesta (AFIP/Bancos)
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    PARSING_ERROR = "PARSING_ERROR"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"

    # Errores de Conectividad AFIP
    AFIP_UNAVAILABLE = "AFIP_UNAVAILABLE"
    AFIP_AUTH_FAILED = "AFIP_AUTH_FAILED"
    AFIP_RATE_LIMITED = "AFIP_RATE_LIMITED"

    # Errores Contables
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"

    # Errores Internos
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"

class BusinessException(Exception):
    def __init__(self, code: BusinessErrorCode, details: str = ""):
        self.code = code.value
        self.details = details
        super().__init__(f"[{self.code}] {self.details}")