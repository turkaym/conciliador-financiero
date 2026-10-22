from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
import re
import unicodedata


NORMALIZER_VERSION = "ref-nfkd-v1"
RULE_VERSION = "match-v1"


@dataclass(frozen=True)
class MatchInput:
    movement_id: int
    movement_date: date
    movement_amount: Decimal
    movement_currency: str
    movement_reference: str | None
    receipt_id: int
    receipt_date: date
    receipt_amount: Decimal
    receipt_currency: str
    receipt_reference: str | None


@dataclass(frozen=True)
class MatchResult:
    movement_id: int
    receipt_id: int
    exact_match: bool
    reference_score: Decimal
    day_difference: int
    movement_normalized: str
    receipt_normalized: str
    movement_tokens: tuple[str, ...]
    receipt_tokens: tuple[str, ...]

    @property
    def explanation(self) -> dict[str, object]:
        return {
            "movement_normalized": self.movement_normalized,
            "receipt_normalized": self.receipt_normalized,
            "movement_tokens": list(self.movement_tokens),
            "receipt_tokens": list(self.receipt_tokens),
        }


def normalize_reference(value: str | None) -> tuple[str, tuple[str, ...]]:
    decomposed = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    uppercase = without_marks.upper()
    without_punctuation = "".join(" " if unicodedata.category(char).startswith("P") else char for char in uppercase)
    collapsed = " ".join(without_punctuation.split())
    tokens = tuple(sorted(set(re.findall(r"\S+", collapsed))))
    return collapsed, tokens


def _jaccard(left: set[str], right: set[str]) -> Decimal:
    union = left | right
    return Decimal(0) if not union else Decimal(len(left & right)) / Decimal(len(union))


def evaluate_pair(pair: MatchInput) -> MatchResult | None:
    if pair.movement_currency != "ARS" or pair.receipt_currency != "ARS":
        return None
    if pair.movement_amount != pair.receipt_amount:
        return None
    day_difference = (pair.receipt_date - pair.movement_date).days
    if abs(day_difference) > 3:
        return None
    movement_normalized, movement_tokens = normalize_reference(pair.movement_reference)
    receipt_normalized, receipt_tokens = normalize_reference(pair.receipt_reference)
    return MatchResult(
        movement_id=pair.movement_id,
        receipt_id=pair.receipt_id,
        exact_match=bool(movement_normalized and movement_normalized == receipt_normalized),
        reference_score=_jaccard(set(movement_tokens), set(receipt_tokens)),
        day_difference=day_difference,
        movement_normalized=movement_normalized,
        receipt_normalized=receipt_normalized,
        movement_tokens=movement_tokens,
        receipt_tokens=receipt_tokens,
    )


def rank_matches(matches: list[MatchResult]) -> list[MatchResult]:
    return sorted(matches, key=lambda item: (-item.exact_match, -item.reference_score, abs(item.day_difference), item.movement_id, item.receipt_id))


def evaluation_fingerprint(pair: MatchInput) -> bytes:
    payload = {
        "movement_date": pair.movement_date.isoformat(),
        "movement_amount": str(pair.movement_amount),
        "movement_currency": pair.movement_currency,
        "movement_reference": pair.movement_reference,
        "receipt_date": pair.receipt_date.isoformat(),
        "receipt_amount": str(pair.receipt_amount),
        "receipt_currency": pair.receipt_currency,
        "receipt_reference": pair.receipt_reference,
        "normalizer_version": NORMALIZER_VERSION,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).digest()
