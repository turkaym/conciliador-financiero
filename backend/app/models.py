from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, JSON, LargeBinary, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column("activo", Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "creado_en", DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DataSource(Base):
    __tablename__ = "fuente_datos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_type: Mapped[str] = mapped_column("tipo_origen", String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column("nombre", String(120), nullable=False)
    active: Mapped[bool] = mapped_column("activa", Boolean, nullable=False)


class ImportTemplate(Base):
    __tablename__ = "plantilla_importacion"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column("fuente_id", BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    template_type: Mapped[str] = mapped_column("tipo", String(20), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column("activa", Boolean, nullable=False)


class TemplateField(Base):
    __tablename__ = "campo_plantilla"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    template_id: Mapped[int] = mapped_column("plantilla_id", BigInteger, nullable=False)
    source_column: Mapped[str] = mapped_column("columna_origen", String(120), nullable=False)
    canonical_field: Mapped[str] = mapped_column("campo_canonico", String(80), nullable=False)
    data_type: Mapped[str | None] = mapped_column("tipo_dato", String(20))
    required: Mapped[bool | None] = mapped_column("requerido", Boolean)
    date_format: Mapped[str | None] = mapped_column("formato_fecha", String(40))
    decimal_separator: Mapped[str | None] = mapped_column("separador_decimal", String(1))


class ImportBatch(Base):
    __tablename__ = "lote_carga"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    source_id: Mapped[int] = mapped_column("fuente_id", BigInteger, nullable=False)
    template_id: Mapped[int | None] = mapped_column("plantilla_id", BigInteger)
    requested_template: Mapped[str] = mapped_column("plantilla_solicitada", String(120), nullable=False)
    user_id: Mapped[int] = mapped_column("usuario_id", BigInteger, nullable=False)
    batch_type: Mapped[str] = mapped_column("tipo", String(20), nullable=False)
    file_name: Mapped[str] = mapped_column("nombre_archivo", String(255), nullable=False)
    file_hash: Mapped[bytes] = mapped_column("huella_archivo", LargeBinary(32), nullable=False)
    file_content: Mapped[bytes] = mapped_column("contenido_archivo", LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column("estado", String(30), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        "recibido_en", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column("finalizado_en", DateTime(timezone=True))
    original_batch_id: Mapped[int | None] = mapped_column("lote_original_id", BigInteger)


class ImportedRecord(Base):
    __tablename__ = "registro_importado"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    batch_id: Mapped[int] = mapped_column("lote_id", BigInteger, nullable=False)
    source_id: Mapped[int] = mapped_column("fuente_id", BigInteger, nullable=False)
    row_number: Mapped[int] = mapped_column("numero_fila", Integer, nullable=False)
    record_type: Mapped[str] = mapped_column("tipo", String(20), nullable=False)
    status: Mapped[str] = mapped_column("estado", String(30), nullable=False)
    external_id: Mapped[str | None] = mapped_column("id_externo", String(120))
    duplicate_key: Mapped[bytes] = mapped_column("clave_duplicado", LargeBinary(32), nullable=False)
    original_record_id: Mapped[int | None] = mapped_column("registro_original_id", BigInteger)
    original_data: Mapped[dict] = mapped_column("datos_originales", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column("creado_en", DateTime(timezone=True), server_default=func.now(), nullable=False)


class BankMovement(Base):
    __tablename__ = "movimiento_bancario"

    record_id: Mapped[int] = mapped_column("registro_id", BigInteger, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column("moneda", String(3), nullable=False)
    normalized_reference: Mapped[str | None] = mapped_column("referencia_normalizada", Text)
    is_credit: Mapped[bool] = mapped_column("es_credito", Boolean, nullable=False)


class Receipt(Base):
    __tablename__ = "comprobante"

    record_id: Mapped[int] = mapped_column("registro_id", BigInteger, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column("moneda", String(3), nullable=False)
    normalized_reference: Mapped[str | None] = mapped_column("referencia_normalizada", Text)
    category: Mapped[str] = mapped_column("clase", String(20), nullable=False)


class ValidationError(Base):
    __tablename__ = "error_validacion"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    batch_id: Mapped[int] = mapped_column("lote_id", BigInteger, nullable=False)
    record_id: Mapped[int | None] = mapped_column("registro_id", BigInteger)
    scope: Mapped[str] = mapped_column("alcance", String(10), nullable=False)
    field: Mapped[str | None] = mapped_column("campo", String(120))
    code: Mapped[str] = mapped_column("codigo", String(60), nullable=False)
    message: Mapped[str] = mapped_column("mensaje", Text, nullable=False)
    original_record_id: Mapped[int | None] = mapped_column("registro_original_id", BigInteger)
    created_at: Mapped[datetime] = mapped_column("creado_en", DateTime(timezone=True), server_default=func.now(), nullable=False)
