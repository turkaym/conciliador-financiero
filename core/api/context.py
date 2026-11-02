import contextvars
from typing import Optional

# Variables de contexto aisladas por cada Task asíncrona (petición HTTP)
_audit_user_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar("audit_user_id", default=None)
_audit_ip_address: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("audit_ip_address", default=None)
_audit_tenant_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar("audit_tenant_id", default=None)

def set_audit_user_id(user_id: int):
    _audit_user_id.set(user_id)

def get_audit_user_id() -> Optional[int]:
    return _audit_user_id.get()

def set_audit_ip_address(ip: str):
    _audit_ip_address.set(ip)

def get_audit_ip_address() -> Optional[str]:
    return _audit_ip_address.get()

def set_audit_tenant_id(tenant_id: int):
    _audit_tenant_id.set(tenant_id)

def get_audit_tenant_id() -> Optional[int]:
    return _audit_tenant_id.get()