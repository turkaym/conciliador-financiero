import logging
import os
import tempfile
from datetime import datetime
from sqlalchemy import delete
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from core.tasks.celery_config import app
from core.database.session import tenant_session_ctx
from core.database.models.sistema import PadronFiscal, HistorialIngestaPadron
from core.storage.minio_client import minio_client

logger = logging.getLogger("WORKER_PADRONES")

CHUNK_SIZE = 10000

@app.task(bind=True, max_retries=3)
def procesar_padron_fiscal(
    self,
    tenant_id: str,
    bucket_name: str,
    object_name: str,
    jurisdiccion: str,
    periodo: str,
    entidad_id: int,
    **kwargs
):
    """
    Worker asíncrono para ingesta masiva de padrones de retención.
    Arquitectura K8s-Ready: Descarga desde MinIO, procesa en memoria constante y autodestruye evidencias.
    Aislamiento Multi-Tenant: Segmentación matemática por Entidad con Upsert resiliente.
    """
    logger.info(f"Iniciando procesamiento de padrón {jurisdiccion} - Período {periodo} para tenant {tenant_id} - Entidad {entidad_id}")

    historial_id = None

    # 🌟 TELEMETRÍA: Registrar inicio de proceso garantizado
    with tenant_session_ctx(tenant_id) as db:
        registro_historial = HistorialIngestaPadron(
            entidad_id=entidad_id,
            jurisdiccion=jurisdiccion,
            periodo=periodo,
            nombre_archivo=object_name,
            estado="PROCESANDO",
            tarea_celery_id=self.request.id
        )
        db.add(registro_historial)
        db.commit()
        db.refresh(registro_historial)
        historial_id = registro_historial.id

    # Generación de archivo efímero local dentro del contenedor del worker
    fd, temp_file_path = tempfile.mkstemp(suffix=".txt", prefix=f"worker_padron_")
    os.close(fd)

    try:
        # 🌟 DESACOPLAMIENTO K8S: Descarga desde el storage distribuido
        try:
            minio_client.download_file(tenant_schema=tenant_id, object_name=object_name, dest_path=temp_file_path)
        except Exception as e:
            logger.error(f"Fallo al descargar {object_name} desde MinIO: {e}")
            raise ValueError(f"No se pudo descargar el padrón desde el storage: {e}")

        # 🌟 ESCUDO DE VALIDACIÓN (FAIL-FAST) CON DISEÑO OFICIAL
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            primera_linea = f.readline().strip()

            if jurisdiccion.upper() == "ARBA":
                if len(primera_linea.split(';')) < 11:
                    raise ValueError("[BUSINESS_LOGIC] El archivo no coincide con el diseño de registro oficial del Padrón de ARBA (Delimitador ';').")

            elif jurisdiccion.upper() == "AGIP":
                if "CUIT" not in primera_linea.upper():
                    raise ValueError("[BUSINESS_LOGIC] El archivo no coincide con el formato oficial del Padrón de AGIP.")

        # 🌟 FIX: Se eliminó el "DELETE" previo destructivo. Confiamos 100% en la idempotencia del Upsert.

        with tenant_session_ctx(tenant_id) as db:
            registros_procesados = 0
            lote_actual = []

            # 🌟 SANEAMIENTO: Motor de Upsert encapsulado (DRY)
            def _ejecutar_upsert(lote):
                if not lote:
                    return 0
                # Deduplicación en memoria para evitar CardinalityViolation
                lote_dedup = list({(r['entidad_id'], r['cuit'], r['jurisdiccion'], r['periodo']): r for r in lote}.values())

                stmt_insert = insert(PadronFiscal).values(lote_dedup)
                stmt_upsert = stmt_insert.on_conflict_do_update(
                    index_elements=['entidad_id', 'cuit', 'jurisdiccion', 'periodo'],
                    set_={
                        'alicuota_retencion': stmt_insert.excluded.alicuota_retencion,
                        'alicuota_percepcion': stmt_insert.excluded.alicuota_percepcion,
                        'updated_at': func.now()
                    }
                )
                db.execute(stmt_upsert)
                db.commit()
                return len(lote) # Devolvemos la longitud original para la telemetría

            # 🌟 PERFORMANCE: Lectura perezosa (Lazy Loading)
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                for index, linea in enumerate(f):
                    linea = linea.strip()
                    if not linea:
                        continue

                    if index == 0 and jurisdiccion.upper() == "AGIP" and "CUIT" in linea.upper():
                        continue

                    try:
                        if jurisdiccion.upper() == "ARBA":
                            partes = linea.split(';')
                            cuit = partes[3].strip()
                            percepcion = float(partes[7].strip().replace(',', '.'))
                            retencion = float(partes[8].strip().replace(',', '.'))
                        else:
                            cuit = linea[0:11].strip()
                            retencion = float(linea[11:17].strip().replace(',', '.'))
                            percepcion = float(linea[17:23].strip().replace(',', '.'))

                        lote_actual.append({
                            "entidad_id": entidad_id,
                            "jurisdiccion": jurisdiccion,
                            "cuit": cuit,
                            "periodo": periodo,
                            "alicuota_retencion": retencion,
                            "alicuota_percepcion": percepcion
                        })
                    except (ValueError, IndexError):
                        logger.warning(f"Línea malformada ignorada en línea {index + 1}: {linea}")
                        continue

                    # Inserción en bloques (Chunking)
                    if len(lote_actual) >= CHUNK_SIZE:
                        registros_procesados += _ejecutar_upsert(lote_actual)
                        lote_actual = []

            # Insertar el remanente final
            registros_procesados += _ejecutar_upsert(lote_actual)

        if registros_procesados == 0:
            raise ValueError("[BUSINESS_LOGIC] El archivo fue procesado pero no se encontró ningún registro válido para importar.")

        logger.info(f"✅ Padrón {jurisdiccion} procesado exitosamente. {registros_procesados} registros impactados.")

        # 🌟 TELEMETRÍA: Registrar éxito
        if historial_id:
            with tenant_session_ctx(tenant_id) as db:
                db.query(HistorialIngestaPadron).filter(
                    HistorialIngestaPadron.id == historial_id
                ).update({
                    "estado": "EXITO",
                    "registros_insertados": registros_procesados,
                    "finalizado_el": func.now()
                })
                db.commit()

        return {"status": "success", "insertados": registros_procesados}

    except ValueError as ve:
        logger.error(f"Rechazo de negocio: {str(ve)}")
        if historial_id:
            with tenant_session_ctx(tenant_id) as db:
                db.query(HistorialIngestaPadron).filter(
                    HistorialIngestaPadron.id == historial_id
                ).update({
                    "estado": "FALLO",
                    "mensaje_error": str(ve)[:500],
                    "finalizado_el": func.now()
                })
                db.commit()
        raise ve

    except Exception as e:
        logger.error(f"Fallo crítico procesando padrón: {str(e)}", exc_info=True)
        if historial_id:
            with tenant_session_ctx(tenant_id) as db:
                # 🌟 SANEAMIENTO: Persistencia del error crudo en telemetría
                db.query(HistorialIngestaPadron).filter(
                    HistorialIngestaPadron.id == historial_id
                ).update({
                    "estado": "FALLO",
                    "mensaje_error": f"Fallo interno en orquestador. Error original: {str(e)[:250]}",
                    "finalizado_el": func.now()
                })
                db.commit()
        raise self.retry(exc=e, countdown=60)

    finally:
        # 🌟 FIX ARQUITECTÓNICO: Limpieza garantizada sin importar el estado final de la tarea
        # 1. Borramos el archivo temporal del disco del worker
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass

        # 2. Purgamos el crudo original en MinIO para evitar Storage Leak
        try:
            minio_client.client.remove_object(bucket_name, object_name)
            logger.info(f"🧹 [STORAGE] Archivo {object_name} purgado exitosamente de MinIO.")
        except Exception as e:
            logger.error(f"❌ [STORAGE] Fuga de datos menor. Fallo al eliminar {object_name} en MinIO: {e}")