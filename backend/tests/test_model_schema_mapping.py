from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import BankMovement, Receipt


def test_movement_and_receipt_persist_using_approved_physical_columns():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE movimiento_bancario (
                registro_id INTEGER PRIMARY KEY,
                fecha DATE NOT NULL,
                monto NUMERIC(18, 2) NOT NULL,
                moneda VARCHAR(3) NOT NULL,
                referencia_normalizada TEXT,
                es_credito BOOLEAN NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE comprobante (
                registro_id INTEGER PRIMARY KEY,
                fecha DATE NOT NULL,
                monto NUMERIC(18, 2) NOT NULL,
                moneda VARCHAR(3) NOT NULL,
                referencia_normalizada TEXT,
                clase VARCHAR(20) NOT NULL
            )
            """
        )

    with Session(engine) as session:
        session.add_all(
            [
                BankMovement(
                    record_id=1,
                    date=date(2026, 10, 28),
                    amount=Decimal("125.50"),
                    currency="ARS",
                    normalized_reference="invoice-1",
                    is_credit=True,
                ),
                Receipt(
                    record_id=2,
                    date=date(2026, 10, 27),
                    amount=Decimal("125.50"),
                    currency="ARS",
                    normalized_reference="invoice-1",
                    category="VENTA",
                ),
            ]
        )
        session.commit()

        movement = session.scalar(select(BankMovement).where(BankMovement.record_id == 1))
        receipt = session.scalar(select(Receipt).where(Receipt.record_id == 2))

    assert movement is not None
    assert movement.date == date(2026, 10, 28)
    assert movement.amount == Decimal("125.50")
    assert receipt is not None
    assert receipt.date == date(2026, 10, 27)
    assert receipt.amount == Decimal("125.50")
