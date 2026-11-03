import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from config.feature_flags import feature_flags
from core.api.v1.endpoints.system import get_capabilities
from core.tasks.celery_config import app as celery_app


ROOT = Path(__file__).resolve().parents[1]


def load_gateway_app():
    source = ROOT / "services/api-gateway/main.py"
    if not source.exists():
        source = ROOT / "main.py"
    spec = importlib.util.spec_from_file_location("feature_test_gateway", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def route_paths(app):
    return set(app.openapi()["paths"])


class FeatureCompositionTests(unittest.TestCase):
    def test_ai_rules_route_requires_enabled_and_implemented_state(self):
        class FeatureStateOverride:
            def __init__(self, enabled, implemented):
                self.enabled = enabled
                self.implemented = implemented

            def usable(self, identifier):
                if identifier == "ai_rules":
                    return self.enabled and self.implemented
                return feature_flags.usable(identifier)

        for state in (FeatureStateOverride(False, True), FeatureStateOverride(True, False)):
            with self.subTest(state=state.__dict__), patch("config.feature_flags.feature_flags", state):
                self.assertNotIn("/v1/ai-rules", route_paths(load_gateway_app()))

    def test_disabled_and_enabled_api_routes_are_composed_from_manifest(self):
        app = load_gateway_app()
        paths = route_paths(app)

        self.assertNotIn("/v1/matching/status/{schema_name}", paths)
        self.assertNotIn("/v1/ai/chat", paths)
        self.assertNotIn("/v1/b2b/api-keys", paths)
        self.assertIn("/v1/ai-rules", paths)
        self.assertIn("/v1/ai-rules/{rule_id}", paths)
        self.assertIn("/v1/bancos/cuentas", paths)
        self.assertIn("/v1/pagos/ordenes", paths)
        self.assertIn("/v1/padrones/historial", paths)
        self.assertIn("/v1/equipo/", paths)

        capabilities = get_capabilities()
        self.assertTrue(all(set(item) == {"identifier", "enabled", "implemented", "usable"} for item in capabilities))
        ai_rules = next(item for item in capabilities if item["identifier"] == "ai_rules")
        self.assertEqual(ai_rules, {
            "identifier": "ai_rules", "enabled": True, "implemented": True, "usable": True,
        })

    def test_disabled_feature_schedules_are_absent(self):
        schedule = celery_app.conf.beat_schedule

        self.assertNotIn("run-auto-matching-every-15-mins", schedule)
        self.assertNotIn("run-outbox-sweeper-every-10-secs", schedule)
        self.assertIn("run-fiscal-auditor-daily", schedule)
        self.assertIn("run-sincronizacion-moneda-diaria", schedule)

    def test_disabled_exclusive_task_invocation_fails_closed(self):
        from core.tasks.maintenance_tasks import run_tenant_matching_task

        self.assertFalse(feature_flags.usable("reconciliation"))
        with self.assertRaisesRegex(RuntimeError, "reconciliation"):
            run_tenant_matching_task("tenant_test")
