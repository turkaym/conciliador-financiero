import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


FEATURE_IDENTIFIERS = (
    "b2b_directory",
    "expenses_payments",
    "tax_registries",
    "team",
    "ai_rules",
    "reconciliation",
    "ai_copilot",
    "b2b_integrations",
)

IMPLEMENTATION_READINESS = MappingProxyType({
    "b2b_directory": True,
    "expenses_payments": True,
    "tax_registries": True,
    "team": True,
    "ai_rules": True,
    "reconciliation": True,
    "ai_copilot": True,
    "b2b_integrations": True,
})


class FeatureManifestError(RuntimeError):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FeatureManifestError(f"Feature manifest contains duplicate key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class FeatureState:
    enabled: Mapping[str, bool]

    def usable(self, identifier: str) -> bool:
        return self.enabled.get(identifier, False) and IMPLEMENTATION_READINESS.get(identifier, False)

    @property
    def capabilities(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "identifier": identifier,
                "enabled": self.enabled[identifier],
                "implemented": IMPLEMENTATION_READINESS[identifier],
                "usable": self.usable(identifier),
            }
            for identifier in FEATURE_IDENTIFIERS
        )


def load_feature_manifest(path: Path) -> FeatureState:
    try:
        document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except FeatureManifestError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise FeatureManifestError(f"Feature manifest could not be loaded: {exc}") from exc

    if not isinstance(document, dict) or set(document) != {"version", "features"}:
        raise FeatureManifestError("Feature manifest must contain only version and features")
    if type(document["version"]) is not int or document["version"] != 1:
        raise FeatureManifestError("Feature manifest version is unsupported")

    features = document["features"]
    if not isinstance(features, dict):
        raise FeatureManifestError("Feature manifest features must be an object")
    missing = set(FEATURE_IDENTIFIERS) - set(features)
    unknown = set(features) - set(FEATURE_IDENTIFIERS)
    if missing or unknown:
        raise FeatureManifestError(
            f"Feature manifest identifiers are invalid (missing={sorted(missing)}, unknown={sorted(unknown)})"
        )
    if any(type(value) is not bool for value in features.values()):
        raise FeatureManifestError("Feature manifest values must be booleans")

    return FeatureState(MappingProxyType(dict(features)))


feature_flags = load_feature_manifest(Path(__file__).with_name("feature_flags.json"))
