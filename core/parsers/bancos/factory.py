import inspect
from typing import Dict, Type
from core.parsers.interfaces import BaseParser

# Importaciones de adaptadores estáticos
from core.parsers.bancos.santander_parser import SantanderCSVParser
from core.parsers.bancos.galicia_parser import GaliciaExcelParser
from core.parsers.bancos.mercadopago_parser import MercadoPagoCSVParser
from core.parsers.bancos.macro_parser import BancoMacroParser
from core.parsers.bancos.prisma_parser import PrismaParser_v1

# Importación del nuevo adaptador heurístico
from core.parsers.bancos.dynamic_parser import DynamicParser

class BancosFactory:
    """
    Patrón Factory: Aísla la instanciación de adaptadores bancarios.
    """
    _parsers: Dict[str, Type[BaseParser]] = {
        "SANTANDER_CSV": SantanderCSVParser,
        "GALICIA_XLSX": GaliciaExcelParser,
        "MERCADO_PAGO_CSV": MercadoPagoCSVParser,
        "MACRO_CSV": BancoMacroParser,
        "DYNAMIC_XRAY": DynamicParser,
        "PRISMA_V1": PrismaParser_v1,
    }

    @classmethod
    def get_parser(cls, parser_code: str, cuenta_id: int, cuenta_contable_id: int, **kwargs) -> BaseParser:
        """
        🌟 FIX FASE A: Inyección de Dependencias Contables Obligatoria.
        Retorna la instancia del parser o falla rápido si no existe.
        """
        parser_class = cls._parsers.get(parser_code.upper())
        if not parser_class:
            raise ValueError(f"[BUSINESS_LOGIC] Parser de banco no soportado: {parser_code}")

        # Inyectamos obligatoriamente el contexto financiero
        kwargs["cuenta_id"] = cuenta_id
        kwargs["cuenta_contable_id"] = cuenta_contable_id

        # Introspección dinámica para proteger código Legacy
        sig = inspect.signature(parser_class.__init__)
        valid_params = sig.parameters

        accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in valid_params.values())

        if accepts_kwargs:
            filtered_kwargs = kwargs
        else:
            # Drenamos los argumentos modernos que harían explotar a un parser viejo,
            # pero preservando cuenta_id y cuenta_contable_id que ahora son exigidos por BaseParser.
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params or k in ['cuenta_id', 'cuenta_contable_id']}

        return parser_class(**filtered_kwargs)