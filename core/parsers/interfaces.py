from abc import ABC, abstractmethod
from typing import Iterator, TypeVar, Generic
from decimal import Decimal
import logging

from core.utils.validators import IntegridadContableValidator

logger = logging.getLogger("PARSER_FACTORY")

T = TypeVar('T')

class BaseParser(ABC, Generic[T]):
    """
    [DOCUMENTACIÓN ARQUITECTÓNICA V4.0]
    ATENCIÓN DEVS: Esta clase utiliza Metaprogramación (__init_subclass__).
    El método `parse_generator` de cualquier clase hija será envuelto dinámicamente
    para inyectar `cuenta_id`, inicializar `saldo_pendiente` y ejecutar validaciones
    matemáticas estrictas (Fail-Fast) ANTES de ceder (yield) el registro a la capa de servicios.

    ESTÁ ESTRICTAMENTE PROHIBIDO sobrescribir `__init_subclass__` en las clases bancarias hijas.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if 'parse_generator' not in cls.__dict__:
            return

        original_parse = cls.parse_generator

        def secure_parse_wrapper(self, file_path: str) -> Iterator[T]:
            generator = original_parse(self, file_path)

            for record in generator:
                is_dict = isinstance(record, dict)

                if is_dict:
                    record['cuenta_id'] = getattr(self, 'cuenta_id')
                    record['cuenta_contable_id'] = getattr(self, 'cuenta_contable_id')

                    monto = Decimal(str(record.get('monto', 0)))
                    if 'saldo_pendiente' not in record or record['saldo_pendiente'] is None:
                        record['saldo_pendiente'] = monto

                    saldo = Decimal(str(record['saldo_pendiente']))
                    ref = record.get('concepto_bancario_crudo', 'Sin referencia')
                else:
                    setattr(record, 'cuenta_id', getattr(self, 'cuenta_id'))
                    setattr(record, 'cuenta_contable_id', getattr(self, 'cuenta_contable_id'))

                    monto = Decimal(str(getattr(record, 'monto', 0)))
                    if not hasattr(record, 'saldo_pendiente') or getattr(record, 'saldo_pendiente') is None:
                        setattr(record, 'saldo_pendiente', monto)

                    saldo = Decimal(str(getattr(record, 'saldo_pendiente')))
                    ref = getattr(record, 'concepto_bancario_crudo', 'Sin referencia')

                IntegridadContableValidator.validar_paridad_movimiento(monto, saldo, ref)
                yield record

        # 🌟 FIX: Visibilidad absoluta en consola durante el arranque del sistema
        logger.info(f"🛡️ [METAPROGRAMACIÓN] Inyectando Escudo de Integridad en el parser heredado: {cls.__name__}")
        cls.parse_generator = secure_parse_wrapper

    def __init__(self, cuenta_id: int, cuenta_contable_id: int, **kwargs):
        if not cuenta_id or not cuenta_contable_id:
            raise ValueError("[BUSINESS_LOGIC] Instanciación bloqueada: Todo parser requiere cuenta_id y cuenta_contable_id.")

        self.cuenta_id = cuenta_id
        self.cuenta_contable_id = cuenta_contable_id

        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    def validate_format(self, file_path: str) -> None:
        pass

    @abstractmethod
    def parse_generator(self, file_path: str) -> Iterator[T]:
        pass