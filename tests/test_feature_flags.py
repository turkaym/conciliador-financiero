import json
import tempfile
import unittest
from pathlib import Path

from config.feature_flags import (
    FeatureManifestError,
    IMPLEMENTATION_READINESS,
    load_feature_manifest,
)


AUTHORIZED_DEFAULTS = {
    "b2b_directory": True,
    "expenses_payments": True,
    "tax_registries": True,
    "team": True,
    "ai_rules": True,
    "reconciliation": False,
    "ai_copilot": False,
    "b2b_integrations": False,
}


def write_manifest(tmp_path, features=AUTHORIZED_DEFAULTS, version=1):
    path = tmp_path / "feature_flags.json"
    path.write_text(json.dumps({"version": version, "features": features}), encoding="utf-8")
    return path


class FeatureManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_authorized_manifest_and_safe_capabilities(self):
        state = load_feature_manifest(write_manifest(self.path))

        self.assertEqual(dict(state.enabled), AUTHORIZED_DEFAULTS)
        self.assertFalse(state.enabled["reconciliation"])
        self.assertTrue(IMPLEMENTATION_READINESS["ai_rules"])
        self.assertTrue(all(set(item) == {"identifier", "enabled", "implemented", "usable"} for item in state.capabilities))
        self.assertTrue(all(item["usable"] == (item["enabled"] and item["implemented"]) for item in state.capabilities))

    def test_invalid_feature_sets_fail_closed(self):
        invalid_sets = [
            {key: value for key, value in AUTHORIZED_DEFAULTS.items() if key != "team"},
            {**AUTHORIZED_DEFAULTS, "unknown": True},
            {**AUTHORIZED_DEFAULTS, "team": "true"},
        ]
        for features in invalid_sets:
            with self.subTest(features=features), self.assertRaises(FeatureManifestError):
                load_feature_manifest(write_manifest(self.path, features))

    def test_duplicate_and_unsupported_version_fail_closed(self):
        duplicate = self.path / "duplicate.json"
        duplicate.write_text(
            '{"version":1,"features":{"b2b_directory":true,"b2b_directory":false}}',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(FeatureManifestError, "duplicate"):
            load_feature_manifest(duplicate)
        with self.assertRaisesRegex(FeatureManifestError, "version"):
            load_feature_manifest(write_manifest(self.path, version=2))
