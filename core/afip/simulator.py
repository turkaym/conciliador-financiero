import random
from datetime import datetime, timedelta
from .wsfe import BaseFiscalProvider

class SimulatedWSFEClient(BaseFiscalProvider):
    """
    Simulador de Grado Industrial.
    Imita el comportamiento de ARCA sin latencia ni errores de certificado.
    """
    def __init__(self, environment="sim"):
        self.environment = environment

    def get_last_voucher_number(self, punto_venta: int, tipo_cbte: int) -> int:
        # Simulamos que hay 15 facturas en el servidor
        return 15

    def get_voucher_details(self, nro: int, punto_venta: int, tipo_cbte: int) -> dict:
        """Genera un comprobante aleatorio pero con estructura real."""
        logger_name = "SIMULATOR"
        # Simulamos una demora de red realista
        import time; time.sleep(0.2)

        return {
            "tipo_cbte": tipo_cbte,
            "punto_venta": punto_venta,
            "numero": nro,
            "fecha_emision": (datetime.now() - timedelta(days=random.randint(0, 30))).date(),
            "cuit_receptor": f"20{random.randint(10000000, 99999999)}9",
            "importe_total": round(random.uniform(1000, 50000), 2),
            "moneda": "PES",
            "cae": f"740{random.randint(1000000000, 9999999999)}",
            "vencimiento_cae": (datetime.now() + timedelta(days=10)).date()
        }