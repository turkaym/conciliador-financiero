import unittest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.api.deps import CachedTenant, CachedUser, get_current_user, get_tenant_db_session
from core.api.v1.endpoints.ai_rules import router
from core.database.models.contabilidad import ReglaAprendizaje
from core.database.models.entidades import RazonSocialPropia
from core.database.models.sistema import LogAuditoria
from core.database.session import audit_after_flush, receive_checkin, setup_postgresql_extensions
from core.matching.transactions import aprender_regla


event.remove(Engine, "first_connect", setup_postgresql_extensions)
event.remove(Engine, "checkin", receive_checkin)
event.remove(Session, "after_flush", audit_after_flush)


def make_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for table in (RazonSocialPropia.__table__, ReglaAprendizaje.__table__, LogAuditoria.__table__):
        table.create(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def make_user(role="admin", tenant_id=1, schema="tenant_a", entitled=True):
    tenant = CachedTenant(
        tenant_id, schema, True, features={"ai_rules": True} if entitled else {},
        subscription_status="active",
    )
    return CachedUser(7, "admin@example.com", role, True, tenant, "admin@example.com")


class AiRulesTests(unittest.TestCase):
    def setUp(self):
        self.sessions = {"tenant_a": make_session(), "tenant_b": make_session()}
        for session in self.sessions.values():
            session.add(RazonSocialPropia(
                id=1, cuit="30712345678", nombre_fantasia="Test",
                razon_social="Test SA", is_active=True,
            ))
            session.commit()
        self.user = make_user()
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        app.dependency_overrides[get_current_user] = lambda: self.user

        def tenant_db():
            yield self.sessions[self.user.tenant.schema_name]

        app.dependency_overrides[get_tenant_db_session] = tenant_db
        self.app = app
        self.client = TestClient(app)
        self.headers = {"X-Entity-ID": "1"}

    def tearDown(self):
        for session in self.sessions.values():
            session.close()

    def create_rule(self, **changes):
        payload = {
            "tipo_regla": "concepto_cuit",
            "patron_concepto": "  pago   proveedor  ",
            "cuit_asociado": "30-71234567-8",
            "tipo_cbte_asociado": 1,
        }
        payload.update(changes)
        return self.client.post("/v1/ai-rules", headers=self.headers, json=payload)

    def test_model_mapping_and_matching_writer_remain_compatible(self):
        columns = set(ReglaAprendizaje.__table__.columns.keys())
        self.assertEqual(
            columns,
            {"id", "entidad_id", "patron_concepto", "cuit_asociado",
             "tipo_cbte_asociado", "frecuencia_uso", "activa", "created_at", "updated_at"},
        )
        cbte = type("Cbte", (), {"cuit_receptor": "30712345678", "tipo_cbte_afip": 1})()
        aprender_regla(self.sessions["tenant_a"], "PAGO 123", cbte, 1)
        self.sessions["tenant_a"].flush()
        self.assertEqual(self.sessions["tenant_a"].query(ReglaAprendizaje).one().entidad_id, 1)

    def test_management_happy_paths_and_bounded_filters(self):
        created = self.create_rule()
        self.assertEqual(created.status_code, 201)
        rule = created.json()
        self.assertEqual(rule["patron_concepto"], "PAGO PROVEEDOR")
        self.assertEqual(rule["cuit_asociado"], "30712345678")

        listed = self.client.get(
            "/v1/ai-rules?limit=10&offset=0&activa=true&buscar=PAGO", headers=self.headers
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["total"], 1)
        self.assertEqual(self.client.get(
            f"/v1/ai-rules/{rule['id']}", headers=self.headers
        ).status_code, 200)

        updated = self.client.patch(
            f"/v1/ai-rules/{rule['id']}", headers=self.headers,
            json={"activa": False, "expected_updated_at": rule["updated_at"]},
        )
        self.assertEqual(updated.status_code, 200)
        deactivated = self.client.delete(
            f"/v1/ai-rules/{rule['id']}?expected_updated_at={updated.json()['updated_at']}",
            headers=self.headers,
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertFalse(deactivated.json()["activa"])
        self.assertEqual(self.sessions["tenant_a"].query(LogAuditoria).count(), 3)

    def test_invalid_unsupported_not_found_and_conflict_are_sanitized(self):
        invalid = self.create_rule(tipo_regla="llm_prompt", cuit_asociado="tenant_a")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json(), {"detail": "Datos de regla inválidos."})
        self.assertNotIn("tenant_a", invalid.text)

        missing = self.client.get("/v1/ai-rules/999", headers=self.headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "Regla no encontrada."})

        rule = self.create_rule().json()
        stale = datetime(2000, 1, 1, tzinfo=timezone.utc).isoformat()
        conflict = self.client.patch(
            f"/v1/ai-rules/{rule['id']}", headers=self.headers,
            json={"activa": False, "expected_updated_at": stale},
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json(), {"detail": "La regla fue modificada por otra operación."})

    def test_tenant_authority_is_dependency_only(self):
        rule_id = self.create_rule().json()["id"]
        injected = self.create_rule(tenant_id=2, schema_name="tenant_b")
        self.assertEqual(injected.status_code, 400)
        self.user = make_user(tenant_id=2, schema="tenant_b")
        self.assertEqual(
            self.client.get(f"/v1/ai-rules/{rule_id}", headers=self.headers).status_code, 404
        )

    def test_audit_failure_rolls_back_without_leaking_details(self):
        def fail_audit(*_):
            raise SQLAlchemyError("tenant_a secret")

        event.listen(LogAuditoria, "before_insert", fail_audit)
        try:
            response = self.create_rule()
        finally:
            event.remove(LogAuditoria, "before_insert", fail_audit)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "No se pudo completar la operación."})
        self.assertNotIn("tenant_a", response.text)
        self.assertEqual(self.sessions["tenant_a"].query(ReglaAprendizaje).count(), 0)

    def test_unauthenticated_and_unauthorized_are_rejected(self):
        self.user = make_user(role="operador")
        self.assertEqual(self.client.get("/v1/ai-rules", headers=self.headers).status_code, 403)
        del self.app.dependency_overrides[get_current_user]
        response = self.client.get("/v1/ai-rules", headers=self.headers)
        self.assertEqual(response.status_code, 401)

    def test_tenant_without_entitlement_is_rejected(self):
        self.user = make_user(entitled=False)
        self.assertEqual(self.client.get("/v1/ai-rules", headers=self.headers).status_code, 403)


if __name__ == "__main__":
    unittest.main()
