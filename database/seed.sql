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

COMMIT;
