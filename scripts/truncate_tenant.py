# Concepto para el futuro (No ejecutar ahora)
def truncate_tenant_data(db, schema_name):
    # Desactiva chequeos de Foreign Key temporalmente para poder limpiar en orden aleatorio
    db.execute(text("SET session_replication_role = 'replica';"))

    # Vacía las tablas operativas de tu tenant específico sin tocar su existencia ni sus roles
    db.execute(text(f"""
        TRUNCATE TABLE
        "{schema_name}".comprobantes,
        "{schema_name}".movimientos_tesoreria,
        "{schema_name}".movimientos_bancarios,
        "{schema_name}".ordenes_pago,
        "{schema_name}".contactos_comerciales
        CASCADE;
    """))

    db.execute(text("SET session_replication_role = 'origin';"))
    db.commit()