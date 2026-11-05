import os
import logging
import httpx
from typing import Optional, List, Dict, Any

logger = logging.getLogger("BANK_PROMETEO")
logger.setLevel(logging.INFO)

class PrometeoClient:
    def __init__(self):
        self.api_key = os.getenv("PROMETEO_API_KEY", "dummy_key")
        self.env = os.getenv("PROMETEO_ENV", "sandbox")

        # Enrutamiento dinámico basado en el entorno
        if self.env.lower() == "production":
            self.base_url = "https://banking.prometeoapi.com"
        else:
            self.base_url = "https://banking.sandbox.prometeoapi.com"

        self.headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json"
        }

    async def login(self, provider: str, username: str, password: str) -> Optional[str]:
        """Autenticación asíncrona usando form-urlencoded como pide Prometeo."""
        url = f"{self.base_url}/login/"
        payload = {"provider": provider, "username": username, "password": password}

        try:
            logger.info(f"🔄 Iniciando login asíncrono en {url}...")
            async with httpx.AsyncClient() as client:
                # Prometeo exige data= (x-www-form-urlencoded) en el login
                response = await client.post(url, data=payload, headers=self.headers, timeout=20.0)
                response.raise_for_status()

            data = response.json()
            if data.get("status") in ["success", "logged_in"]:
                logger.info("✅ Login exitoso. Session Key obtenida.")
                return data.get("key")
            else:
                logger.error(f"❌ Fallo en login Prometeo: {data.get('message', data)}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"💥 Error HTTP desde Prometeo: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"💥 Error de red comunicándose con Prometeo: {e}")
            return None

    async def get_accounts(self, session_key: str) -> List[Dict[str, Any]]:
        """Obtiene cuentas bancarias."""
        url = f"{self.base_url}/account/"
        params = {"key": session_key}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params, timeout=20.0)
                response.raise_for_status()

            data = response.json()
            if "accounts" in data:
                logger.info(f"📊 {len(data['accounts'])} cuentas recuperadas.")
                return data["accounts"]
            return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo cuentas: {e}")
            return []

    async def get_transactions(self, session_key: str, account_number: str, currency: str, date_start: str, date_end: str) -> List[Dict[str, Any]]:
        """Obtiene movimientos bancarios."""
        url = f"{self.base_url}/account/{currency}/{account_number}/movement/"
        params = {
            "key": session_key,
            "date_start": date_start,
            "date_end": date_end
        }

        try:
            logger.info(f"📥 Solicitando movimientos asíncronos para {account_number}...")
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params, timeout=30.0)
                response.raise_for_status()

            data = response.json()
            if "movements" in data:
                logger.info(f"📊 {len(data['movements'])} movimientos recuperados.")
                return data["movements"]
            return []
        except Exception as e:
            logger.error(f"❌ Error obteniendo movimientos: {e}")
            return []