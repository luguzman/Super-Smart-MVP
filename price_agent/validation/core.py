"""Validación final previa a cualquier salida."""
from __future__ import annotations

import re
from datetime import date

from price_agent.models import PriceObservation


class ValidationError(ValueError):
    pass


def validate_postal_code(postal_code: str) -> str:
    value = str(postal_code).strip()
    if not re.fullmatch(r"(?:0[1-9]|[1-4][0-9]|5[0-2])[0-9]{3}", value):
        raise ValidationError("El código postal debe ser un CP español válido de cinco dígitos.")
    return value


def validate_observations(observations: list[PriceObservation], catalog_ids: set[str]) -> None:
    errors = []
    for index, item in enumerate(observations, start=1):
        prefix = f"Observación {index}"
        if item.product_id not in catalog_ids:
            errors.append(f"{prefix}: product_id desconocido ({item.product_id})")
        if not item.store.strip():
            errors.append(f"{prefix}: store vacío")
        if item.postal_code:
            try:
                validate_postal_code(item.postal_code)
            except ValidationError:
                errors.append(f"{prefix}: código postal inválido ({item.postal_code})")
        if item.price_eur is None or item.price_eur <= 0:
            errors.append(f"{prefix}: precio ausente o no positivo")
        if item.price_eur is not None and (item.promotion_eur < 0 or item.promotion_eur >= item.price_eur):
            errors.append(f"{prefix}: promoción inválida")
        if not item.observed_on:
            errors.append(f"{prefix}: fecha ausente")
        else:
            try:
                date.fromisoformat(item.observed_on)
            except ValueError:
                errors.append(f"{prefix}: fecha inválida")
    if errors:
        raise ValidationError("; ".join(errors))
