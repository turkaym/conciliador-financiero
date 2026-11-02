import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecretManager:
    def __init__(self):
        master_key = os.getenv("SECRET_KEY", "cambiame_en_produccion_123")
        self.fernet = self._generate_fernet(master_key)

    def _generate_fernet(self, master_key: str) -> Fernet:
        """Deriva una llave de 32 bytes estable a partir de la SECRET_KEY"""
        salt = b'conciliador_salt_static'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)

    # 🌟 FIX C.1: Nuevos métodos KMS para operar 100% en memoria
    def encrypt_string(self, raw_data: str) -> str:
        """Cifra un string en memoria y retorna el hash."""
        if raw_data.startswith('gAAAAA'):
            return raw_data # Ya está cifrado
        encrypted_bytes = self.fernet.encrypt(raw_data.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt_string(self, encrypted_data: str) -> bytes:
        """Descifra un hash de Fernet devolviendo los bytes crudos listos para OpenSSL."""
        return self.fernet.decrypt(encrypted_data.encode('utf-8'))

    # (Mantenemos los métodos viejos por retrocompatibilidad temporal si algún script los usa)
    def encrypt_file(self, file_path: str):
        if not os.path.exists(file_path):
            return
        with open(file_path, "rb") as f:
            data = f.read()
        if data.startswith(b'gAAAAA'):
            return
        encrypted_data = self.fernet.encrypt(data)
        with open(file_path, "wb") as f:
            f.write(encrypted_data)

    def decrypt_to_temp(self, file_path: str):
        with open(file_path, "rb") as f:
            encrypted_data = f.read()
        return self.fernet.decrypt(encrypted_data)