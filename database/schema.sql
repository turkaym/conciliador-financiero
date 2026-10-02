BEGIN;
SET TIME ZONE 'UTC';

CREATE TABLE usuario (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    password_hash TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_usuario_email CHECK (btrim(email) <> ''),
    CONSTRAINT ck_usuario_password_hash CHECK (btrim(password_hash) <> '')
);
CREATE UNIQUE INDEX uq_usuario_email_ci ON usuario (lower(email));

CREATE TABLE fuente_datos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo_origen VARCHAR(20) NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_fuente_datos_codigo UNIQUE (codigo),
    CONSTRAINT uq_fuente_datos_id_tipo UNIQUE (id, tipo_origen),
    CONSTRAINT ck_fuente_datos_tipo CHECK (tipo_origen IN ('BANCO', 'COMPROBANTES')),
    CONSTRAINT ck_fuente_datos_codigo CHECK (btrim(codigo) <> ''),
    CONSTRAINT ck_fuente_datos_nombre CHECK (btrim(nombre) <> '')
);

CREATE TABLE plantilla_importacion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fuente_id BIGINT NOT NULL REFERENCES fuente_datos(id),
    nombre VARCHAR(120) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    version INTEGER NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_plantilla_nombre_version UNIQUE (fuente_id, nombre, tipo, version),
    CONSTRAINT uq_plantilla_fuente_tipo UNIQUE (id, fuente_id, tipo),
    CONSTRAINT ck_plantilla_nombre CHECK (btrim(nombre) <> ''),
    CONSTRAINT ck_plantilla_tipo CHECK (tipo IN ('MOVIMIENTO', 'COMPROBANTE')),
    CONSTRAINT ck_plantilla_version CHECK (version > 0)
);
CREATE INDEX ix_plantilla_fuente_activa ON plantilla_importacion (fuente_id, activa);

CREATE TABLE campo_plantilla (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plantilla_id BIGINT NOT NULL REFERENCES plantilla_importacion(id) ON DELETE CASCADE,
    columna_origen VARCHAR(120) NOT NULL,
    campo_canonico VARCHAR(80) NOT NULL,
    tipo_dato VARCHAR(20) NOT NULL,
    requerido BOOLEAN NOT NULL DEFAULT TRUE,
    formato_fecha VARCHAR(40),
    separador_decimal CHAR(1),
    CONSTRAINT uq_campo_columna UNIQUE (plantilla_id, columna_origen),
    CONSTRAINT uq_campo_canonico UNIQUE (plantilla_id, campo_canonico),
    CONSTRAINT ck_campo_columna CHECK (btrim(columna_origen) <> ''),
    CONSTRAINT ck_campo_canonico CHECK (btrim(campo_canonico) <> ''),
    CONSTRAINT ck_campo_tipo CHECK (tipo_dato IN ('TEXTO', 'FECHA', 'DECIMAL', 'MONEDA', 'CATEGORIA')),
    CONSTRAINT ck_campo_parametros CHECK (
        (tipo_dato = 'FECHA' AND formato_fecha IS NOT NULL AND separador_decimal IS NULL)
        OR (tipo_dato = 'DECIMAL' AND separador_decimal IS NOT NULL AND formato_fecha IS NULL)
        OR (tipo_dato NOT IN ('FECHA', 'DECIMAL') AND formato_fecha IS NULL AND separador_decimal IS NULL)
    )
);

CREATE TABLE lote_carga (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fuente_id BIGINT NOT NULL REFERENCES fuente_datos(id),
    plantilla_id BIGINT,
    plantilla_solicitada VARCHAR(120) NOT NULL,
    usuario_id BIGINT NOT NULL REFERENCES usuario(id),
    tipo VARCHAR(20) NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    huella_archivo BYTEA NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'RECIBIDO',
    lote_original_id BIGINT REFERENCES lote_carga(id),
    recibido_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_en TIMESTAMPTZ,
    CONSTRAINT fk_lote_plantilla_compuesta FOREIGN KEY (plantilla_id, fuente_id, tipo)
        REFERENCES plantilla_importacion(id, fuente_id, tipo),
    CONSTRAINT uq_lote_id_fuente_tipo UNIQUE (id, fuente_id, tipo),
    CONSTRAINT ck_lote_tipo CHECK (tipo IN ('MOVIMIENTO', 'COMPROBANTE')),
    CONSTRAINT ck_lote_estado CHECK (estado IN ('RECIBIDO', 'EN_VALIDACION', 'PROCESADO', 'PROCESADO_CON_ERRORES', 'FALLIDO', 'DUPLICADO')),
    CONSTRAINT ck_lote_plantilla_solicitada CHECK (btrim(plantilla_solicitada) <> ''),
    CONSTRAINT ck_lote_nombre_archivo CHECK (btrim(nombre_archivo) <> ''),
    CONSTRAINT ck_lote_huella CHECK (octet_length(huella_archivo) = 32),
    CONSTRAINT ck_lote_plantilla_resuelta CHECK (plantilla_id IS NOT NULL OR estado IN ('FALLIDO', 'DUPLICADO')),
    CONSTRAINT ck_lote_duplicado CHECK ((estado = 'DUPLICADO') = (lote_original_id IS NOT NULL)),
    CONSTRAINT ck_lote_original_distinto CHECK (lote_original_id IS NULL OR lote_original_id <> id),
    CONSTRAINT ck_lote_finalizacion CHECK (
        (estado IN ('PROCESADO', 'PROCESADO_CON_ERRORES', 'FALLIDO', 'DUPLICADO')) = (finalizado_en IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_lote_huella_original ON lote_carga (fuente_id, tipo, huella_archivo)
    WHERE estado <> 'DUPLICADO';
CREATE INDEX ix_lote_usuario_fecha ON lote_carga (usuario_id, recibido_en DESC);
CREATE INDEX ix_lote_fuente_tipo_estado ON lote_carga (fuente_id, tipo, estado);
CREATE INDEX ix_lote_original ON lote_carga (lote_original_id) WHERE lote_original_id IS NOT NULL;

CREATE TABLE registro_importado (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lote_id BIGINT NOT NULL,
    fuente_id BIGINT NOT NULL REFERENCES fuente_datos(id),
    numero_fila INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'IMPORTADO',
    id_externo VARCHAR(120),
    clave_duplicado BYTEA NOT NULL,
    registro_original_id BIGINT REFERENCES registro_importado(id),
    datos_originales JSONB NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_registro_lote_fuente_tipo FOREIGN KEY (lote_id, fuente_id, tipo)
        REFERENCES lote_carga(id, fuente_id, tipo),
    CONSTRAINT uq_registro_lote_fila UNIQUE (lote_id, numero_fila),
    CONSTRAINT ck_registro_fila CHECK (numero_fila > 1),
    CONSTRAINT ck_registro_tipo CHECK (tipo IN ('MOVIMIENTO', 'COMPROBANTE')),
    CONSTRAINT ck_registro_estado CHECK (estado IN ('IMPORTADO', 'INVALIDO', 'PENDIENTE', 'CON_PROPUESTAS', 'CONCILIADO')),
    CONSTRAINT ck_registro_id_externo CHECK (id_externo IS NULL OR btrim(id_externo) <> ''),
    CONSTRAINT ck_registro_clave CHECK (octet_length(clave_duplicado) = 32),
    CONSTRAINT ck_registro_original_json CHECK (jsonb_typeof(datos_originales) = 'object'),
    CONSTRAINT ck_registro_duplicado CHECK (registro_original_id IS NULL OR (estado = 'INVALIDO' AND registro_original_id <> id))
);
CREATE UNIQUE INDEX uq_registro_clave_elegible ON registro_importado (fuente_id, tipo, clave_duplicado)
    WHERE estado <> 'INVALIDO';
CREATE INDEX ix_registro_lote_estado_tipo ON registro_importado (lote_id, estado, tipo);
CREATE INDEX ix_registro_fuente_externo ON registro_importado (fuente_id, tipo, id_externo) WHERE id_externo IS NOT NULL;
CREATE INDEX ix_registro_original ON registro_importado (registro_original_id) WHERE registro_original_id IS NOT NULL;

CREATE TABLE movimiento_bancario (
    registro_id BIGINT PRIMARY KEY REFERENCES registro_importado(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    monto NUMERIC(18,2) NOT NULL,
    moneda CHAR(3) NOT NULL,
    referencia_normalizada TEXT,
    es_credito BOOLEAN NOT NULL,
    CONSTRAINT ck_movimiento_monto CHECK (monto > 0),
    CONSTRAINT ck_movimiento_moneda CHECK (moneda = 'ARS'),
    CONSTRAINT ck_movimiento_credito CHECK (es_credito)
);
CREATE INDEX ix_movimiento_matching ON movimiento_bancario (moneda, monto, fecha);

CREATE TABLE comprobante (
    registro_id BIGINT PRIMARY KEY REFERENCES registro_importado(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    monto NUMERIC(18,2) NOT NULL,
    moneda CHAR(3) NOT NULL,
    referencia_normalizada TEXT,
    clase VARCHAR(20) NOT NULL,
    CONSTRAINT ck_comprobante_monto CHECK (monto > 0),
    CONSTRAINT ck_comprobante_moneda CHECK (moneda = 'ARS'),
    CONSTRAINT ck_comprobante_clase CHECK (clase IN ('VENTA', 'COBRO'))
);
CREATE INDEX ix_comprobante_matching ON comprobante (moneda, monto, fecha);

CREATE TABLE error_validacion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lote_carga(id),
    registro_id BIGINT REFERENCES registro_importado(id),
    alcance VARCHAR(10) NOT NULL,
    campo VARCHAR(120),
    codigo VARCHAR(60) NOT NULL,
    mensaje TEXT NOT NULL,
    registro_original_id BIGINT REFERENCES registro_importado(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_error_alcance CHECK (alcance IN ('LOTE', 'FILA')),
    CONSTRAINT ck_error_objetivo CHECK ((alcance = 'LOTE' AND registro_id IS NULL) OR (alcance = 'FILA' AND registro_id IS NOT NULL)),
    CONSTRAINT ck_error_codigo CHECK (btrim(codigo) <> ''),
    CONSTRAINT ck_error_mensaje CHECK (btrim(mensaje) <> '')
);
CREATE INDEX ix_error_lote ON error_validacion (lote_id, creado_en);
CREATE INDEX ix_error_registro ON error_validacion (registro_id) WHERE registro_id IS NOT NULL;

CREATE TABLE propuesta_conciliacion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    movimiento_id BIGINT NOT NULL REFERENCES movimiento_bancario(registro_id),
    comprobante_id BIGINT NOT NULL REFERENCES comprobante(registro_id),
    estado VARCHAR(20) NOT NULL DEFAULT 'GENERADA',
    normalizador_version VARCHAR(30) NOT NULL,
    version_regla VARCHAR(30) NOT NULL,
    score_referencia NUMERIC(5,4) NOT NULL,
    coincidencia_exacta BOOLEAN NOT NULL,
    diferencia_dias SMALLINT NOT NULL,
    explicacion JSONB NOT NULL,
    motivo_decision TEXT,
    decidida_por BIGINT REFERENCES usuario(id),
    decidida_en TIMESTAMPTZ,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_propuesta_pareja UNIQUE (id, movimiento_id, comprobante_id),
    CONSTRAINT ck_propuesta_estado CHECK (estado IN ('GENERADA', 'CONFIRMADA', 'RECHAZADA', 'CADUCADA')),
    CONSTRAINT ck_propuesta_normalizador CHECK (btrim(normalizador_version) <> ''),
    CONSTRAINT ck_propuesta_version CHECK (btrim(version_regla) <> ''),
    CONSTRAINT ck_propuesta_score CHECK (score_referencia BETWEEN 0 AND 1),
    CONSTRAINT ck_propuesta_dias CHECK (diferencia_dias BETWEEN -3 AND 3),
    CONSTRAINT ck_propuesta_explicacion CHECK (jsonb_typeof(explicacion) = 'object'),
    CONSTRAINT ck_propuesta_decision CHECK (
        (estado = 'GENERADA' AND motivo_decision IS NULL AND decidida_por IS NULL AND decidida_en IS NULL)
        OR (estado = 'CONFIRMADA' AND motivo_decision IS NULL AND decidida_por IS NOT NULL AND decidida_en IS NOT NULL)
        OR (estado = 'RECHAZADA' AND coalesce(btrim(motivo_decision), '') <> '' AND decidida_por IS NOT NULL AND decidida_en IS NOT NULL)
        OR (estado = 'CADUCADA' AND decidida_por IS NULL AND decidida_en IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_propuesta_generada ON propuesta_conciliacion (movimiento_id, comprobante_id, version_regla)
    WHERE estado = 'GENERADA';
CREATE UNIQUE INDEX uq_propuesta_rechazada ON propuesta_conciliacion (movimiento_id, comprobante_id, version_regla)
    WHERE estado = 'RECHAZADA';
CREATE INDEX ix_propuesta_estado_fecha ON propuesta_conciliacion (estado, creado_en DESC);
CREATE INDEX ix_propuesta_movimiento ON propuesta_conciliacion (movimiento_id);
CREATE INDEX ix_propuesta_comprobante ON propuesta_conciliacion (comprobante_id);

CREATE TABLE conciliacion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    propuesta_id BIGINT NOT NULL UNIQUE,
    movimiento_id BIGINT NOT NULL REFERENCES movimiento_bancario(registro_id),
    comprobante_id BIGINT NOT NULL REFERENCES comprobante(registro_id),
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVA',
    confirmada_por BIGINT NOT NULL REFERENCES usuario(id),
    confirmada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    revertida_por BIGINT REFERENCES usuario(id),
    revertida_en TIMESTAMPTZ,
    motivo_reversion TEXT,
    CONSTRAINT fk_conciliacion_propuesta_pareja FOREIGN KEY (propuesta_id, movimiento_id, comprobante_id)
        REFERENCES propuesta_conciliacion(id, movimiento_id, comprobante_id),
    CONSTRAINT ck_conciliacion_estado CHECK (estado IN ('ACTIVA', 'REVERTIDA')),
    CONSTRAINT ck_conciliacion_reversion CHECK (
        (estado = 'ACTIVA' AND revertida_por IS NULL AND revertida_en IS NULL AND motivo_reversion IS NULL)
        OR (estado = 'REVERTIDA' AND revertida_por IS NOT NULL AND revertida_en IS NOT NULL AND coalesce(btrim(motivo_reversion), '') <> '')
    )
);
CREATE UNIQUE INDEX uq_conciliacion_movimiento_activa ON conciliacion (movimiento_id) WHERE estado = 'ACTIVA';
CREATE UNIQUE INDEX uq_conciliacion_comprobante_activa ON conciliacion (comprobante_id) WHERE estado = 'ACTIVA';
CREATE INDEX ix_conciliacion_confirmador ON conciliacion (confirmada_por);
CREATE INDEX ix_conciliacion_reversor ON conciliacion (revertida_por) WHERE revertida_por IS NOT NULL;

CREATE TABLE evento_historial (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id BIGINT REFERENCES usuario(id),
    lote_id BIGINT REFERENCES lote_carga(id),
    registro_id BIGINT REFERENCES registro_importado(id),
    propuesta_id BIGINT REFERENCES propuesta_conciliacion(id),
    conciliacion_id BIGINT REFERENCES conciliacion(id),
    tipo VARCHAR(60) NOT NULL,
    motivo TEXT,
    datos JSONB NOT NULL DEFAULT '{}'::jsonb,
    ocurrido_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_evento_tipo CHECK (btrim(tipo) <> ''),
    CONSTRAINT ck_evento_objetivo CHECK (num_nonnulls(lote_id, registro_id, propuesta_id, conciliacion_id) = 1),
    CONSTRAINT ck_evento_datos CHECK (jsonb_typeof(datos) = 'object'),
    CONSTRAINT ck_evento_humano CHECK (tipo NOT IN ('PROPUESTA_CONFIRMADA', 'PROPUESTA_RECHAZADA', 'CONCILIACION_REVERTIDA') OR usuario_id IS NOT NULL),
    CONSTRAINT ck_evento_motivo CHECK (tipo NOT IN ('PROPUESTA_RECHAZADA', 'CONCILIACION_REVERTIDA') OR coalesce(btrim(motivo), '') <> '')
);
CREATE INDEX ix_evento_lote_fecha ON evento_historial (lote_id, ocurrido_en DESC) WHERE lote_id IS NOT NULL;
CREATE INDEX ix_evento_registro_fecha ON evento_historial (registro_id, ocurrido_en DESC) WHERE registro_id IS NOT NULL;
CREATE INDEX ix_evento_propuesta_fecha ON evento_historial (propuesta_id, ocurrido_en DESC) WHERE propuesta_id IS NOT NULL;
CREATE INDEX ix_evento_conciliacion_fecha ON evento_historial (conciliacion_id, ocurrido_en DESC) WHERE conciliacion_id IS NOT NULL;
CREATE INDEX ix_evento_usuario_fecha ON evento_historial (usuario_id, ocurrido_en DESC) WHERE usuario_id IS NOT NULL;

CREATE FUNCTION validar_plantilla_fuente_tipo() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE origen VARCHAR(20);
BEGIN
    SELECT tipo_origen INTO origen FROM fuente_datos WHERE id = NEW.fuente_id;
    IF (NEW.tipo = 'MOVIMIENTO' AND origen <> 'BANCO')
       OR (NEW.tipo = 'COMPROBANTE' AND origen <> 'COMPROBANTES') THEN
        RAISE EXCEPTION 'plantilla tipo % incompatible con fuente %', NEW.tipo, origen;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_plantilla_fuente_tipo BEFORE INSERT OR UPDATE ON plantilla_importacion
    FOR EACH ROW EXECUTE FUNCTION validar_plantilla_fuente_tipo();

CREATE FUNCTION proteger_datos_originales() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.datos_originales IS DISTINCT FROM OLD.datos_originales THEN
        RAISE EXCEPTION 'datos_originales es inmutable';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_registro_original_inmutable BEFORE UPDATE ON registro_importado
    FOR EACH ROW EXECUTE FUNCTION proteger_datos_originales();

CREATE FUNCTION validar_subtipo_registro() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    registro_ids BIGINT[];
    registro_id_actual BIGINT;
    tipo_actual VARCHAR(20);
    estado_actual VARCHAR(30);
    movimientos INTEGER;
    comprobantes INTEGER;
BEGIN
    IF TG_TABLE_NAME = 'registro_importado' THEN
        registro_ids := ARRAY[coalesce(NEW.id, OLD.id)];
    ELSE
        registro_ids := ARRAY[NEW.registro_id, OLD.registro_id];
    END IF;

    FOREACH registro_id_actual IN ARRAY registro_ids LOOP
        CONTINUE WHEN registro_id_actual IS NULL;

        SELECT tipo, estado
          INTO tipo_actual, estado_actual
          FROM registro_importado
         WHERE id = registro_id_actual;
        CONTINUE WHEN NOT FOUND;

        SELECT count(*) INTO movimientos FROM movimiento_bancario WHERE registro_id = registro_id_actual;
        SELECT count(*) INTO comprobantes FROM comprobante WHERE registro_id = registro_id_actual;

        IF estado_actual = 'INVALIDO' AND movimientos + comprobantes <> 0 THEN
            RAISE EXCEPTION 'registro invalido no admite subtipo';
        ELSIF estado_actual <> 'INVALIDO' AND tipo_actual = 'MOVIMIENTO'
              AND (movimientos <> 1 OR comprobantes <> 0) THEN
            RAISE EXCEPTION 'registro movimiento requiere subtipo exacto';
        ELSIF estado_actual <> 'INVALIDO' AND tipo_actual = 'COMPROBANTE'
              AND (comprobantes <> 1 OR movimientos <> 0) THEN
            RAISE EXCEPTION 'registro comprobante requiere subtipo exacto';
        END IF;
    END LOOP;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER tr_registro_subtipo_exacto AFTER INSERT OR UPDATE ON registro_importado
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validar_subtipo_registro();
CREATE CONSTRAINT TRIGGER tr_movimiento_subtipo_exacto AFTER INSERT OR UPDATE OR DELETE ON movimiento_bancario
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validar_subtipo_registro();
CREATE CONSTRAINT TRIGGER tr_comprobante_subtipo_exacto AFTER INSERT OR UPDATE OR DELETE ON comprobante
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validar_subtipo_registro();

CREATE FUNCTION validar_actualizacion_propuesta() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.movimiento_id, NEW.comprobante_id, NEW.normalizador_version, NEW.version_regla,
        NEW.score_referencia, NEW.coincidencia_exacta, NEW.diferencia_dias, NEW.explicacion)
       IS DISTINCT FROM
       (OLD.movimiento_id, OLD.comprobante_id, OLD.normalizador_version, OLD.version_regla,
        OLD.score_referencia, OLD.coincidencia_exacta, OLD.diferencia_dias, OLD.explicacion) THEN
        RAISE EXCEPTION 'identidad y evaluacion de propuesta son inmutables';
    END IF;
    IF OLD.estado <> 'GENERADA' OR NEW.estado NOT IN ('CONFIRMADA', 'RECHAZADA', 'CADUCADA') THEN
        RAISE EXCEPTION 'transicion de propuesta no permitida: % -> %', OLD.estado, NEW.estado;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_propuesta_actualizacion_valida BEFORE UPDATE ON propuesta_conciliacion
    FOR EACH ROW EXECUTE FUNCTION validar_actualizacion_propuesta();

CREATE FUNCTION proteger_propuesta_generada() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.estado = 'GENERADA' THEN
        PERFORM id
          FROM registro_importado
         WHERE id IN (NEW.movimiento_id, NEW.comprobante_id)
         ORDER BY id
         FOR UPDATE;

        IF EXISTS (
            SELECT 1
              FROM conciliacion
             WHERE estado = 'ACTIVA'
               AND (movimiento_id IN (NEW.movimiento_id, NEW.comprobante_id)
                    OR comprobante_id IN (NEW.movimiento_id, NEW.comprobante_id))
        ) THEN
            RAISE EXCEPTION 'propuesta generada incompatible con conciliacion activa';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_propuesta_generada_sin_conciliacion
    BEFORE INSERT OR UPDATE ON propuesta_conciliacion
    FOR EACH ROW EXECUTE FUNCTION proteger_propuesta_generada();

CREATE FUNCTION preparar_conciliacion_activa() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.estado = 'ACTIVA' THEN
        PERFORM id
          FROM registro_importado
         WHERE id IN (NEW.movimiento_id, NEW.comprobante_id)
         ORDER BY id
         FOR UPDATE;

        IF NOT EXISTS (
            SELECT 1
              FROM propuesta_conciliacion
             WHERE id = NEW.propuesta_id
               AND movimiento_id = NEW.movimiento_id
               AND comprobante_id = NEW.comprobante_id
               AND estado = 'CONFIRMADA'
        ) THEN
            RAISE EXCEPTION 'conciliacion activa requiere propuesta confirmada para la misma pareja';
        END IF;

        UPDATE propuesta_conciliacion
           SET estado = 'CADUCADA', decidida_en = now()
         WHERE estado = 'GENERADA'
           AND id <> NEW.propuesta_id
           AND (movimiento_id IN (NEW.movimiento_id, NEW.comprobante_id)
                OR comprobante_id IN (NEW.movimiento_id, NEW.comprobante_id));
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_conciliacion_activa_caduca_propuestas
    BEFORE INSERT OR UPDATE ON conciliacion
    FOR EACH ROW EXECUTE FUNCTION preparar_conciliacion_activa();

COMMIT;
