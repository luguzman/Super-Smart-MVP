"""Jerarquía estricta de matching definida en la especificación."""
from __future__ import annotations

from dataclasses import dataclass

from price_agent.models import NormalizedProduct
from price_agent.normalization import normalize_text


@dataclass(frozen=True)
class MatchResult:
    level: int
    score: float
    auto_import: bool
    explanation: str


def _key(value: str) -> str:
    return normalize_text(value).casefold()


def _same_format(left: NormalizedProduct, right: NormalizedProduct) -> bool:
    return (
        left.amount is not None
        and right.amount is not None
        and left.unit == right.unit
        and abs(left.amount - right.amount) < 1e-9
    )


def match_products(expected: NormalizedProduct, candidate: NormalizedProduct) -> MatchResult:
    if expected.ean and candidate.ean and expected.ean == candidate.ean:
        return MatchResult(1, 1.0, True, "EAN idéntico.")
    same_brand = bool(expected.brand and candidate.brand and _key(expected.brand) == _key(candidate.brand))
    same_name = bool(expected.name and candidate.name and _key(expected.name) == _key(candidate.name))
    if same_brand and same_name and _same_format(expected, candidate):
        return MatchResult(2, 0.98, True, "Marca, nombre y formato idénticos.")
    same_category = bool(expected.category and candidate.category and _key(expected.category) == _key(candidate.category))
    if same_brand and same_category and _same_format(expected, candidate):
        return MatchResult(3, 0.78, False, "Marca, categoría y formato compatibles; requiere revisión.")
    if same_category:
        return MatchResult(4, 0.55, False, "Equivalente funcional por categoría; requiere revisión.")
    return MatchResult(4, 0.0, False, "Sin evidencia suficiente; no importar.")
