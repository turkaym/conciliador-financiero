from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, LargeBinary, String, Text, func
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
