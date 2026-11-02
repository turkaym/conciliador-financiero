import re
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any

# ==========================================
# ESQUEMAS DE ENTRADA (Input)
# ==========================================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    company_name: str
    cuit: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres.')
        if not re.search(r"[A-Z]", v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula.')
        if not re.search(r"[a-z]", v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula.')
        if not re.search(r"[0-9]", v):
            raise ValueError('La contraseña debe contener al menos un número.')
        return v

    @field_validator('cuit')
    @classmethod
    def validate_cuit(cls, v):
        if not v.isdigit() or len(v) != 11:
            raise ValueError('El CUIT debe contener exactamente 11 números sin guiones.')

        multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        total = sum(int(v[i]) * multiplicadores[i] for i in range(10))
        resto = total % 11
        digito_verificador = 11 - resto

        if digito_verificador == 11:
            digito_verificador = 0
        elif digito_verificador == 10:
            digito_verificador = 9

        if int(v[10]) != digito_verificador:
            raise ValueError('El CUIT ingresado no es válido (Módulo 11 de AFIP).')

        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ==========================================
# ESQUEMAS DE SALIDA (Output - La "Aduana")
# ==========================================
class UserResponse(BaseModel):
    # 🌟 MEJORA: Se agregan campos de identidad para validación Maker-Checker en el Frontend
    id: str
    email: str
    role: str
    tenant_id: str
    # 🌟 FIX FASE 4.1: Permite el paso de Capabilities por la aduana de Pydantic
    permissions: list[str] = []

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user: UserResponse # 🌟 Ahora propagará id, role y permissions correctamente
    features: dict[str, Any] = {}

class TokenData(BaseModel):
    email: Optional[str] = None
    tenant_id: Optional[str] = None
    role: str = "operator"
    # 🌟 FIX FASE 4.1: Sincronización del JWT interno
    permissions: list[str] = []
    features: list | dict = []

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str