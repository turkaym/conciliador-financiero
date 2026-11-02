from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Clase base para todos los modelos de SQLAlchemy.
    Al no definir un __table_args__ = {'schema': ...} explícito,
    SQLAlchemy usará el schema_translate_map dinámico.
    """
    pass