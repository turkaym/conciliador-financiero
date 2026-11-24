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
    ('BANCO', 'BANCO_DEMO', 'Banco demo', TRUE),
    ('COMPROBANTES', 'COMPROBANTES_DEMO', 'Comprobantes demo', TRUE)
ON CONFLICT (codigo) DO UPDATE
SET tipo_origen = EXCLUDED.tipo_origen,
    nombre = EXCLUDED.nombre,
    activa = EXCLUDED.activa;

INSERT INTO plantilla_importacion (fuente_id, nombre, tipo, version, activa)
SELECT f.id, catalog_values.nombre, catalog_values.tipo, catalog_values.version, TRUE
FROM fuente_datos AS f
JOIN (VALUES
    ('BANCO_DEMO', 'movimientos', 'MOVIMIENTO', 1),
    ('COMPROBANTES_DEMO', 'comprobantes', 'COMPROBANTE', 1)
) AS catalog_values(codigo, nombre, tipo, version) ON catalog_values.codigo = f.codigo
ON CONFLICT (fuente_id, nombre, tipo, version) DO UPDATE
SET activa = EXCLUDED.activa;

INSERT INTO campo_plantilla (plantilla_id, columna_origen, campo_canonico, tipo_dato, requerido, formato_fecha, separador_decimal)
SELECT p.id, fields.columna_origen, fields.campo_canonico, fields.tipo_dato, fields.requerido, fields.formato_fecha, fields.separador_decimal
FROM plantilla_importacion AS p
JOIN (VALUES
    ('movimientos', 'MOVIMIENTO', 'id_externo', 'id_externo', 'TEXTO', FALSE, NULL, NULL),
    ('movimientos', 'MOVIMIENTO', 'fecha', 'fecha', 'FECHA', TRUE, 'YYYY-MM-DD', NULL),
    ('movimientos', 'MOVIMIENTO', 'monto', 'monto', 'DECIMAL', TRUE, NULL, '.'),
    ('movimientos', 'MOVIMIENTO', 'moneda', 'moneda', 'MONEDA', TRUE, NULL, NULL),
    ('movimientos', 'MOVIMIENTO', 'referencia', 'referencia', 'TEXTO', FALSE, NULL, NULL),
    ('movimientos', 'MOVIMIENTO', 'tipo_movimiento', 'tipo_movimiento', 'CATEGORIA', TRUE, NULL, NULL),
    ('comprobantes', 'COMPROBANTE', 'id_externo', 'id_externo', 'TEXTO', FALSE, NULL, NULL),
    ('comprobantes', 'COMPROBANTE', 'fecha', 'fecha', 'FECHA', TRUE, 'YYYY-MM-DD', NULL),
    ('comprobantes', 'COMPROBANTE', 'monto', 'monto', 'DECIMAL', TRUE, NULL, '.'),
    ('comprobantes', 'COMPROBANTE', 'moneda', 'moneda', 'MONEDA', TRUE, NULL, NULL),
    ('comprobantes', 'COMPROBANTE', 'referencia', 'referencia', 'TEXTO', FALSE, NULL, NULL),
    ('comprobantes', 'COMPROBANTE', 'clase', 'clase', 'CATEGORIA', TRUE, NULL, NULL)
) AS fields(nombre, tipo, columna_origen, campo_canonico, tipo_dato, requerido, formato_fecha, separador_decimal)
    ON fields.nombre = p.nombre AND fields.tipo = p.tipo
ON CONFLICT (plantilla_id, columna_origen) DO UPDATE
SET campo_canonico = EXCLUDED.campo_canonico,
    tipo_dato = EXCLUDED.tipo_dato,
    requerido = EXCLUDED.requerido,
    formato_fecha = EXCLUDED.formato_fecha,
    separador_decimal = EXCLUDED.separador_decimal;

COMMIT;
