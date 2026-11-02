import os
import json
import logging
from typing import BinaryIO, List
from datetime import timedelta, datetime, timezone
from minio import Minio
from minio.error import S3Error

# IMPORTACIONES PARA LIFECYCLE MANAGEMENT NATIVO
from minio.commonconfig import Filter, ENABLED, ComposeSource
# 🌟 FIX: Importamos AbortIncompleteMultipartUpload para matar los fantasmas de red
from minio.lifecycleconfig import LifecycleConfig, Expiration, Rule, AbortIncompleteMultipartUpload

# IMPORTACIONES PARA POST POLICY (Escudo de Tamaño)
from minio.datatypes import PostPolicy

logger = logging.getLogger("STORAGE_MINIO")
logger.setLevel(logging.INFO)

class MinioManager:
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        access_key = os.getenv("MINIO_ROOT_USER", "admin")
        secret_key = os.getenv("MINIO_ROOT_PASSWORD", "admin")

        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )

    def _get_tenant_vault(self, tenant_schema: str) -> str:
        if not tenant_schema:
            raise ValueError("Capa Storage: Es obligatorio proveer el identificador para operar.")
        return tenant_schema.replace('_', '-')

    def aplicar_politica_lectura_publica(self, bucket_name: str, prefix: str = "tickets_gastos/"):
        """
        Aplica una política de S3 programática para permitir la lectura anónima
        únicamente en un directorio específico (Zero-Trust por defecto, Excepción controlada).
        """
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/{prefix}*"]
                }
            ]
        }
        try:
            self.client.set_bucket_policy(bucket_name, json.dumps(policy))
            logger.info(f"🛡️ [IAC] Política de lectura pública aplicada en S3: {bucket_name}/{prefix}")
        except Exception as e:
            logger.error(f"Fallo al aplicar política S3 en {bucket_name}: {e}")
            raise

    def ensure_tenant_vault(self, tenant_schema: str):
        bucket_name = self._get_tenant_vault(tenant_schema)
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"🪣 Bóveda aislada '{bucket_name}' creada exitosamente.")

                # 🌟 FIX ARQUITECTÓNICO: Ciclo de vida dual implementado
                config = LifecycleConfig(
                    [
                        # Regla 1: Limpia archivos temporales terminados tras 24hs
                        Rule(
                            ENABLED,
                            rule_filter=Filter(prefix="temp/"),
                            rule_id="auto-purge-temp-24h",
                            expiration=Expiration(days=1)
                        ),
                        # Regla 2: Aborta y destruye fragmentos multipart incompletos en todo el bucket tras 24hs
                        Rule(
                            ENABLED,
                            rule_filter=Filter(prefix=""),
                            rule_id="abort-orphan-multiparts-24h",
                            abort_incomplete_multipart_upload=AbortIncompleteMultipartUpload(days_after_initiation=1)
                        )
                    ]
                )
                self.client.set_bucket_lifecycle(bucket_name, config)
                logger.info(f"🧹 [LIFECYCLE] Política de recolección de basura Multipart inyectada en {bucket_name}.")

                # 🌟 IaC: Configuración automática de acceso de lectura
                self.aplicar_politica_lectura_publica(bucket_name)

        except S3Error as e:
            logger.error(f"❌ Error verificando/creando bóveda {bucket_name}: {e}")
            raise

    # ==============================================================
    # ESCUDO PARA ARCHIVOS SIMPLES (< 20MB)
    # ==============================================================
    def generate_presigned_post_policy(
        self,
        tenant_schema: str,
        object_name: str,
        expiry_minutes: int = 15,
        max_mb: int = 20
    ) -> dict:
        bucket_name = self._get_tenant_vault(tenant_schema)
        self.ensure_tenant_vault(tenant_schema)

        try:
            expiration = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
            policy = PostPolicy(bucket_name, expiration)

            policy.add_equals_condition("key", object_name)
            policy.add_content_length_range_condition(1, max_mb * 1024 * 1024)

            return self.client.presigned_post_policy(policy)

        except S3Error as e:
            logger.error(f"❌ Error generando POST Policy blindada para {object_name}: {e}")
            raise

    # ==============================================================
    # INFRAESTRUCTURA MULTIPART (CHUNKS > 20MB)
    # ==============================================================
    def generate_presigned_put_url(self, tenant_schema: str, object_name: str, expiry_minutes: int = 60) -> str:
        bucket_name = self._get_tenant_vault(tenant_schema)
        self.ensure_tenant_vault(tenant_schema)
        try:
            external_host = os.getenv("MINIO_EXTERNAL_URL", "localhost:9000").replace("http://", "").replace("https://", "")
            access_key = os.getenv("MINIO_ROOT_USER", "admin")
            secret_key = os.getenv("MINIO_ROOT_PASSWORD", "admin")

            ephemeral_client = Minio(
                external_host,
                access_key=access_key,
                secret_key=secret_key,
                secure=False,
                region="us-east-1"
            )

            return ephemeral_client.presigned_put_object(
                bucket_name,
                object_name,
                expires=timedelta(minutes=expiry_minutes)
            )
        except S3Error as e:
            logger.error(f"❌ Error generando PUT URL para chunk {object_name}: {e}")
            raise

    def compose_file(self, tenant_schema: str, target_object: str, source_objects: List[str]):
        bucket_name = self._get_tenant_vault(tenant_schema)
        try:
            sources = [ComposeSource(bucket_name, obj) for obj in source_objects]
            self.client.compose_object(bucket_name, target_object, sources)
            logger.info(f"🧩 Archivo multipart '{target_object}' ensamblado exitosamente ({len(sources)} partes).")

            for obj in source_objects:
                try:
                    self.client.remove_object(bucket_name, obj)
                except Exception:
                    pass

        except S3Error as e:
            logger.error(f"❌ Error ensamblando archivo {target_object}: {e}")
            raise

    def quarantine_file(self, tenant_schema: str, object_name: str, task_request_id: str) -> str:
        bucket_name = self._get_tenant_vault(tenant_schema)
        from minio.commonconfig import CopySource

        quarantine_name = f"quarantine/{object_name.split('/')[-1]}_{task_request_id}"
        try:
            self.client.copy_object(
                bucket_name,
                quarantine_name,
                CopySource(bucket_name, object_name)
            )
            logger.info(f"🛡️ [QUARANTINE] Archivo movido a {quarantine_name}")
            return quarantine_name
        except S3Error as e:
            logger.error(f"❌ Error al mover a cuarentena {object_name}: {e}")
            raise

    # ==============================================================
    # OPERACIONES SÍNCRONAS REFACTORIZADAS
    # ==============================================================
    def upload_stream(self, tenant_schema: str, object_name: str, file_data: BinaryIO, file_size: int, content_type: str = "application/octet-stream"):
        bucket_name = self._get_tenant_vault(tenant_schema)
        try:
            self.ensure_tenant_vault(tenant_schema)
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type
            )
            logger.info(f"📤 Stream {object_name} subido directamente a la bóveda {bucket_name}.")
        except S3Error as e:
            logger.error(f"❌ Error subiendo stream {object_name}: {e}")
            raise

    def upload_file(self, tenant_schema: str, object_name: str, file_path: str):
        bucket_name = self._get_tenant_vault(tenant_schema)
        try:
            self.ensure_tenant_vault(tenant_schema)
            self.client.fput_object(bucket_name, object_name, file_path)
            logger.info(f"📤 Archivo {object_name} subido a {bucket_name}.")
        except S3Error as e:
            logger.error(f"❌ Error subiendo archivo {object_name}: {e}")
            raise

    def download_file(self, tenant_schema: str, object_name: str, dest_path: str):
        bucket_name = self._get_tenant_vault(tenant_schema)
        try:
            self.client.fget_object(bucket_name, object_name, dest_path)
            logger.info(f"📥 Archivo {object_name} descargado en {dest_path}.")
        except S3Error as e:
            logger.error(f"❌ Error descargando {object_name} desde {bucket_name}: {e}")
            raise

# Instancia global compartida
minio_client = MinioManager()