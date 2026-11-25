BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM usuario WHERE lower(email) = 'demo@conciliador.local'
    ) THEN
        UPDATE usuario
           SET password_hash = '$argon2id$v=19$m=65536,t=3,p=4$aQSspJ3//ENfXwT+R3YLjw$vB8GV3LVtARTu/X/HjTVVNLOYqgAVDzc3Cc9NrIOfJs',
               activo = TRUE
         WHERE lower(email) = 'demo@conciliador.local';
    ELSE
        INSERT INTO usuario (email, password_hash, activo)
        VALUES (
            'demo@conciliador.local',
            '$argon2id$v=19$m=65536,t=3,p=4$aQSspJ3//ENfXwT+R3YLjw$vB8GV3LVtARTu/X/HjTVVNLOYqgAVDzc3Cc9NrIOfJs',
            TRUE
        );
    END IF;
END $$;

INSERT INTO fuente_datos (tipo_origen, codigo, nombre, activa)
VALUES
    ('BANCO', 'BANCO_NACION', 'Banco Nación', TRUE),
    ('BANCO', 'BANCO_PROVINCIA', 'Banco Provincia', TRUE),
    ('BANCO', 'SANTANDER', 'Santander', TRUE),
    ('BANCO', 'GALICIA', 'Galicia', TRUE),
    ('BANCO', 'BBVA', 'BBVA', TRUE),
    ('BANCO', 'MACRO', 'Banco Macro', TRUE),
    ('BANCO', 'ICBC', 'ICBC', TRUE),
    ('BANCO', 'SUPERVIELLE', 'Supervielle', TRUE),
    ('BANCO', 'NARANJA_X', 'Naranja X', TRUE),
    ('BANCO', 'MERCADO_PAGO_MOVIMIENTOS', 'Mercado Pago', TRUE),
    ('COMPROBANTES', 'MERCADO_PAGO_COMPROBANTES', 'Mercado Pago', TRUE),
    ('COMPROBANTES', 'TIENDA_NUBE', 'Tienda Nube', TRUE),
    ('COMPROBANTES', 'FACTURAS_FISICAS_OCR', 'Facturas físicas (OCR a CSV)', TRUE),
    ('COMPROBANTES', 'ARCA', 'ARCA', TRUE)
ON CONFLICT (codigo) DO UPDATE
SET tipo_origen = EXCLUDED.tipo_origen,
    nombre = EXCLUDED.nombre,
    activa = EXCLUDED.activa;

UPDATE fuente_datos
SET activa = FALSE
WHERE codigo IN ('BANCO_DEMO', 'COMPROBANTES_DEMO');

INSERT INTO plantilla_importacion (fuente_id, nombre, tipo, version, activa)
SELECT f.id, catalog_values.nombre, catalog_values.tipo, catalog_values.version, TRUE
FROM fuente_datos AS f
JOIN (VALUES
    ('BANCO_NACION', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('BANCO_PROVINCIA', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('SANTANDER', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('GALICIA', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('BBVA', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('MACRO', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('ICBC', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('SUPERVIELLE', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('NARANJA_X', 'movimientos_bancarios_generico', 'MOVIMIENTO', 1),
    ('MERCADO_PAGO_MOVIMIENTOS', 'mercado_pago_movimientos', 'MOVIMIENTO', 1),
    ('MERCADO_PAGO_COMPROBANTES', 'mercado_pago_comprobantes', 'COMPROBANTE', 1),
    ('TIENDA_NUBE', 'tienda_nube_ventas', 'COMPROBANTE', 1),
    ('FACTURAS_FISICAS_OCR', 'facturas_fisicas_ocr', 'COMPROBANTE', 1),
    ('ARCA', 'arca_comprobantes', 'COMPROBANTE', 1)
) AS catalog_values(codigo, nombre, tipo, version) ON catalog_values.codigo = f.codigo
ON CONFLICT (fuente_id, nombre, tipo, version) DO UPDATE
SET activa = EXCLUDED.activa;

INSERT INTO campo_plantilla (plantilla_id, columna_origen, campo_canonico, tipo_dato, requerido, formato_fecha, separador_decimal)
SELECT p.id, fields.columna_origen, fields.campo_canonico, fields.tipo_dato, fields.requerido, fields.formato_fecha, fields.separador_decimal
FROM plantilla_importacion AS p
JOIN (VALUES
    ('movimientos_bancarios_generico', 'MOVIMIENTO', 'Referencia', 'id_externo', 'TEXTO', FALSE, NULL, NULL),
    ('movimientos_bancarios_generico', 'MOVIMIENTO', 'Fecha', 'fecha', 'FECHA', TRUE, 'DD/MM/YYYY', NULL),
    ('movimientos_bancarios_generico', 'MOVIMIENTO', 'Crédito', 'monto', 'DECIMAL', TRUE, NULL, ','),
    ('movimientos_bancarios_generico', 'MOVIMIENTO', 'Moneda', 'moneda', 'MONEDA', FALSE, NULL, NULL),
    ('movimientos_bancarios_generico', 'MOVIMIENTO', 'Descripción', 'referencia', 'TEXTO', FALSE, NULL, NULL),

    ('mercado_pago_movimientos', 'MOVIMIENTO', 'SOURCE_ID', 'id_externo', 'TEXTO', TRUE, NULL, NULL),
    ('mercado_pago_movimientos', 'MOVIMIENTO', 'DATE', 'fecha', 'FECHA', TRUE, 'ISO_DATETIME', NULL),
    ('mercado_pago_movimientos', 'MOVIMIENTO', 'REAL_AMOUNT', 'monto', 'DECIMAL', TRUE, NULL, '.'),
    ('mercado_pago_movimientos', 'MOVIMIENTO', 'CURRENCY_ID', 'moneda', 'MONEDA', FALSE, NULL, NULL),
    ('mercado_pago_movimientos', 'MOVIMIENTO', 'EXTERNAL_REFERENCE', 'referencia', 'TEXTO', FALSE, NULL, NULL),
    ('mercado_pago_movimientos', 'MOVIMIENTO', 'TRANSACTION_TYPE', 'tipo_operacion', 'TEXTO', FALSE, NULL, NULL),

    ('mercado_pago_comprobantes', 'COMPROBANTE', 'SOURCE_ID', 'id_externo', 'TEXTO', TRUE, NULL, NULL),
    ('mercado_pago_comprobantes', 'COMPROBANTE', 'DATE', 'fecha', 'FECHA', TRUE, 'ISO_DATETIME', NULL),
    ('mercado_pago_comprobantes', 'COMPROBANTE', 'TRANSACTION_AMOUNT', 'monto', 'DECIMAL', TRUE, NULL, '.'),
    ('mercado_pago_comprobantes', 'COMPROBANTE', 'CURRENCY_ID', 'moneda', 'MONEDA', FALSE, NULL, NULL),
    ('mercado_pago_comprobantes', 'COMPROBANTE', 'EXTERNAL_REFERENCE', 'referencia', 'TEXTO', FALSE, NULL, NULL),
    ('mercado_pago_comprobantes', 'COMPROBANTE', 'TRANSACTION_TYPE', 'tipo_operacion', 'TEXTO', FALSE, NULL, NULL),

    ('tienda_nube_ventas', 'COMPROBANTE', 'Número de orden', 'id_externo', 'TEXTO', TRUE, NULL, NULL),
    ('tienda_nube_ventas', 'COMPROBANTE', 'Fecha', 'fecha', 'FECHA', TRUE, 'DD/MM/YYYY', NULL),
    ('tienda_nube_ventas', 'COMPROBANTE', 'Total', 'monto', 'DECIMAL', TRUE, NULL, ','),
    ('tienda_nube_ventas', 'COMPROBANTE', 'Moneda', 'moneda', 'MONEDA', FALSE, NULL, NULL),
    ('tienda_nube_ventas', 'COMPROBANTE', 'Medio de pago', 'referencia', 'TEXTO', FALSE, NULL, NULL),
    ('tienda_nube_ventas', 'COMPROBANTE', 'Estado del pago', 'estado_pago', 'TEXTO', FALSE, NULL, NULL),

    ('facturas_fisicas_ocr', 'COMPROBANTE', 'Número', 'id_externo', 'TEXTO', TRUE, NULL, NULL),
    ('facturas_fisicas_ocr', 'COMPROBANTE', 'Fecha', 'fecha', 'FECHA', TRUE, 'DD/MM/YYYY', NULL),
    ('facturas_fisicas_ocr', 'COMPROBANTE', 'Importe total', 'monto', 'DECIMAL', TRUE, NULL, ','),
    ('facturas_fisicas_ocr', 'COMPROBANTE', 'Moneda', 'moneda', 'MONEDA', FALSE, NULL, NULL),
    ('facturas_fisicas_ocr', 'COMPROBANTE', 'CAE', 'referencia', 'TEXTO', FALSE, NULL, NULL),
    ('facturas_fisicas_ocr', 'COMPROBANTE', 'CUIT emisor', 'cuit_emisor', 'TEXTO', TRUE, NULL, NULL),
    ('facturas_fisicas_ocr', 'COMPROBANTE', 'Tipo de comprobante', 'tipo_comprobante', 'TEXTO', TRUE, NULL, NULL),
    ('facturas_fisicas_ocr', 'COMPROBANTE', 'Punto de venta', 'punto_venta', 'TEXTO', TRUE, NULL, NULL),

    ('arca_comprobantes', 'COMPROBANTE', 'Número Desde', 'id_externo', 'TEXTO', TRUE, NULL, NULL),
    ('arca_comprobantes', 'COMPROBANTE', 'Fecha', 'fecha', 'FECHA', TRUE, 'YYYY-MM-DD', NULL),
    ('arca_comprobantes', 'COMPROBANTE', 'Imp. Total', 'monto', 'DECIMAL', TRUE, NULL, ','),
    ('arca_comprobantes', 'COMPROBANTE', 'Moneda', 'moneda', 'MONEDA', FALSE, NULL, NULL),
    ('arca_comprobantes', 'COMPROBANTE', 'Cód. Autorización', 'referencia', 'TEXTO', FALSE, NULL, NULL),
    ('arca_comprobantes', 'COMPROBANTE', 'Tipo', 'tipo_comprobante', 'TEXTO', TRUE, NULL, NULL),
    ('arca_comprobantes', 'COMPROBANTE', 'Punto de Venta', 'punto_venta', 'TEXTO', TRUE, NULL, NULL),
    ('arca_comprobantes', 'COMPROBANTE', 'CUIT Receptor', 'cuit_contraparte', 'TEXTO', FALSE, NULL, NULL)
) AS fields(nombre, tipo, columna_origen, campo_canonico, tipo_dato, requerido, formato_fecha, separador_decimal)
    ON fields.nombre = p.nombre AND fields.tipo = p.tipo
ON CONFLICT (plantilla_id, columna_origen) DO UPDATE
SET campo_canonico = EXCLUDED.campo_canonico,
    tipo_dato = EXCLUDED.tipo_dato,
    requerido = EXCLUDED.requerido,
    formato_fecha = EXCLUDED.formato_fecha,
    separador_decimal = EXCLUDED.separador_decimal;

ALTER TABLE propuesta_conciliacion DROP CONSTRAINT IF EXISTS ck_propuesta_dias;
ALTER TABLE propuesta_conciliacion
    ADD CONSTRAINT ck_propuesta_dias
    CHECK (diferencia_dias BETWEEN -32768 AND 32767);

COMMIT;
