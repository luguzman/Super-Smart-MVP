"""Normalización conservadora: conserva originales y no completa datos inciertos."""
from __future__ import annotations

import re
import unicodedata

from price_agent.models import NormalizedProduct


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    return re.sub(r"\s+", " ", text)


def normalize_ean(value: object) -> str:
    text = normalize_text(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text if text.isdigit() and len(text) in {8, 12, 13, 14} else ""


def normalize_catalog_product(row: dict) -> NormalizedProduct:
    weight_g = row.get("weight_g")
    amount = float(weight_g) / 1000 if isinstance(weight_g, (int, float)) and weight_g > 0 else None
    return NormalizedProduct(
        product_id=normalize_text(row.get("id")),
        name=normalize_text(row.get("name")),
        brand=normalize_text(row.get("brand")),
        ean=normalize_ean(row.get("ean")),
        category=normalize_text(row.get("category")),
        amount=amount,
        unit="kg" if amount is not None else None,
        original=dict(row),
    )
