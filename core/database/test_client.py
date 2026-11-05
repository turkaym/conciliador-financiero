import contextlib
from sqlalchemy import event
from sqlalchemy.orm import Session
from core.database.session import engine

@contextlib.contextmanager
def tenant_test_client(schema_name: str):
    """
    Cliente de pruebas Enterprise.
    Enruta al esquema correcto y aísla las pruebas en una transacción virtual.
    Previene la contaminación de datos haciendo rollback absoluto al finalizar.
    """
    # 1. Enrutamiento Dinámico del Inquilino
    tenant_engine = engine.execution_options(schema_translate_map={None: schema_name})
    connection = tenant_engine.connect()

    # 2. Transacción Maestra (Aislamiento físico)
    transaction = connection.begin()
    session = Session(bind=connection)

    # 3. Savepoint (Permite que el código interno haga .commit() lógicos sin impactar el disco)
    session.begin_nested()

    # Reinicia el savepoint automáticamente si la función testeada hace commit
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session_obj, transaction_obj):
        if transaction_obj.nested and not transaction_obj._parent.nested:
            session_obj.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()  # 🧹 Purga total: revierte todo lo hecho en el test
        connection.close()