import time
import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone

import redis
import requests
from lxml import etree
from pydantic import BaseModel
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.x509 import load_pem_x509_certificate

# 🌟 FIX ARQUITECTURA: Importamos el motor de desencriptación correcto
from core.security.crypto import decrypt_private_key

logger = logging.getLogger("AFIP_AUTH")
logger.setLevel(logging.INFO)

# Script Lua para liberación segura de Locks en Redis (Operación O(1) Atómica)
LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

class TokenData(BaseModel):
    token: str
    sign: str
    generation_time: datetime
    expiration_time: datetime

    def is_valid(self, buffer_seconds=600) -> bool:
        # Buffer de seguridad: Consideramos inválido el token 10 mins antes de que muera
        now = datetime.now(timezone.utc)
        if now >= (self.expiration_time - timedelta(seconds=buffer_seconds)):
            return False
        return True

class AfipAuthManager:
    def __init__(self, redis_client: redis.Redis, crt_content: str, encrypted_key: str, environment: str = "homo"):
        self.redis = redis_client
        self.crt_content = crt_content
        self.encrypted_key = encrypted_key
        self.environment = environment

        # Sesión HTTP reutilizable (Context Manager)
        self.http_session = requests.Session()

        if self.environment == "prod":
            self.wsaa_url = "https://wsaa.afip.gov.ar/ws/services/LoginCms"
        else:
            self.wsaa_url = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"

        self.service = "wsfe"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.http_session.close()

    def get_token(self, cuit: str, force_refresh: bool = False) -> TokenData:
        cache_key = f"afip:auth:{cuit}:{self.service}:{self.environment}"
        lock_key = f"{cache_key}:lock"

        if not force_refresh:
            cached_json = self.redis.get(cache_key)
            if cached_json:
                try:
                    token_data = TokenData.model_validate_json(cached_json)
                    if token_data.is_valid():
                        logger.info(f"🟢 [CACHE] Token válido recuperado para {cuit}")
                        return token_data
                except Exception as e:
                    logger.warning(f"Error parseando caché AFIP: {e}")

        # Lock Distribuido Atómico con UUID
        lock_id = str(uuid.uuid4())
        retries = 0

        while retries < 5:
            # Intentamos adquirir el lock (TTL 60s)
            if self.redis.set(lock_key, lock_id, nx=True, ex=60):
                try:
                    logger.info(f"🚀 [WSAA] Negociando nuevo token criptográfico para {cuit}...")
                    new_token = self._perform_auth_handshake()

                    ttl = int((new_token.expiration_time - datetime.now(timezone.utc)).total_seconds())
                    if ttl > 0:
                        self.redis.setex(cache_key, ttl, new_token.model_dump_json())
                        logger.info(f"💾 [REDIS] Token AFIP persistido. Expira en {ttl}s")

                    return new_token
                finally:
                    self.redis.eval(LUA_RELEASE_LOCK, 1, lock_key, lock_id)
            else:
                logger.info(f"⏳ [WSAA] Otro proceso está obteniendo el token para {cuit}. Esperando...")
                time.sleep(2 ** retries) # Exponential Backoff

                if not force_refresh:
                    cached_json = self.redis.get(cache_key)
                    if cached_json:
                        token_data = TokenData.model_validate_json(cached_json)
                        if token_data.is_valid(): return token_data

            retries += 1

        raise RuntimeError(f"Tiempo de espera agotado solicitando token AFIP para {cuit}")

    def _perform_auth_handshake(self) -> TokenData:
        tra_xml = self._create_tra()
        cms = self._sign_tra_in_memory(tra_xml)
        return self._call_wsaa(cms)

    def _create_tra(self) -> bytes:
        unique_id = str(int(time.time()))
        tz_arg = timezone(timedelta(hours=-3)) # AFIP requiere hora Argentina
        now = datetime.now(tz_arg)

        gen_time = now - timedelta(minutes=5)
        exp_time = now + timedelta(minutes=5)

        gen_str = gen_time.strftime('%Y-%m-%dT%H:%M:%S-03:00')
        exp_str = exp_time.strftime('%Y-%m-%dT%H:%M:%S-03:00')

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>{unique_id}</uniqueId>
        <generationTime>{gen_str}</generationTime>
        <expirationTime>{exp_str}</expirationTime>
    </header>
    <service>{self.service}</service>
</loginTicketRequest>"""

        return xml.encode('utf-8')

    def _sign_tra_in_memory(self, xml_data: bytes) -> str:
        try:
            # 🌟 FIX CRIPTOGRÁFICO: Utilizamos el módulo homologado del core
            decrypted_key_str = decrypt_private_key(self.encrypted_key)
            if not decrypted_key_str:
                raise ValueError("La llave privada retornó vacía.")
            decrypted_key_bytes = decrypted_key_str.encode('utf-8')
        except Exception as e:
            logger.error(f"❌ Error crítico al descifrar llave en bóveda: {e}")
            raise RuntimeError("Corrupción en anillo de llaves criptográficas de AFIP.")

        try:
            cert = load_pem_x509_certificate(self.crt_content.encode('utf-8'))
            private_key = serialization.load_pem_private_key(decrypted_key_bytes, password=None)

            builder = pkcs7.PKCS7SignatureBuilder().set_data(xml_data)
            builder = builder.add_signer(cert, private_key, SHA256())

            cms_bytes = builder.sign(serialization.Encoding.DER, [])
            return base64.b64encode(cms_bytes).decode('utf-8')

        except Exception as e:
            logger.error(f"Error criptográfico en memoria: {str(e)}")
            raise RuntimeError("Fallo en firma digital CMS In-Memory para AFIP.")

    def _call_wsaa(self, cms_b64: str) -> TokenData:
        envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">
   <soapenv:Header/>
   <soapenv:Body>
      <wsaa:loginCms>
         <in0>{cms_b64}</in0>
      </wsaa:loginCms>
   </soapenv:Body>
</soapenv:Envelope>"""

        headers = {'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': ''}

        try:
            response = self.http_session.post(self.wsaa_url, data=envelope, headers=headers, timeout=20)
            if response.status_code == 500:
                logger.error(f"❌ Rechazo de Negocio ARCA (SOAP Fault): {response.text}")

            # 🌟 FIX: SOAP usa HTTP 500 para errores de validación. No cortamos la ejecución si es 500,
            # dejamos que el parseador XML extraiga el 'faultstring'.
            if response.status_code not in (200, 500):
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Falla de conectividad en túnel ARCA: {str(e)}")

        try:
            secure_parser = etree.XMLParser(resolve_entities=False, no_network=True)
            root = etree.fromstring(response.content, parser=secure_parser)

            fault = root.xpath('//*[local-name()="faultstring"]')
            if fault:
                # 🌟 Acá capturamos el mensaje exacto (ej: "Certificado no emitido por AC de confianza")
                raise RuntimeError(f"ARCA Denegó el acceso: {fault[0].text}")

            login_return_node = root.xpath('//*[local-name()="loginCmsReturn"]')
            if not login_return_node:
                raise RuntimeError("La respuesta de ARCA es anómala (falta loginCmsReturn).")

            ticket_xml = login_return_node[0].text
            ticket_root = etree.fromstring(ticket_xml.encode('utf-8'), parser=secure_parser)

            token = ticket_root.xpath('//*[local-name()="token"]')[0].text
            sign = ticket_root.xpath('//*[local-name()="sign"]')[0].text
            expiration_str = ticket_root.xpath('//*[local-name()="expirationTime"]')[0].text

            expiration_dt = datetime.fromisoformat(expiration_str)

            logger.info("🟢 Cripto-Ticket de acceso WSAA obtenido con éxito.")
            return TokenData(
                token=token,
                sign=sign,
                generation_time=datetime.now(timezone.utc),
                expiration_time=expiration_dt
            )

        except etree.XMLSyntaxError as xml_err:
            logger.error(f"❌ Fallo de sintaxis XML (ARCA devolvió HTML/Basura): {xml_err}")
            raise RuntimeError(f"Corrupción en payload de respuesta de ARCA.")
        except RuntimeError:
            raise  # Dejamos pasar los errores de negocio limpios
        except Exception as e:
            logger.error(f"❌ Error de procesamiento del Ticket: {e}")
            raise RuntimeError(f"Fallo estructural en procesamiento de WSAA.")