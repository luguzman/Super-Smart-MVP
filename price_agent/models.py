"""Modelos compartidos, serializables y sin dependencias externas."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class NormalizedProduct:
    product_id: str
    name: str
    brand: str = ""
    ean: str = ""
    category: str = ""
    amount: float | None = None
    unit: str | None = None
    original: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PriceObservation:
    product_id: str
    store: str
    price_eur: float | None
    observed_on: str | None
    promotion_eur: float = 0.0
    loyalty_required: bool = False
    source: str = "manual_csv"
    source_url: str = ""
    notes: str = ""
    availability: str = "unknown"
    confidence: str = "medium"
    unit_price_eur: float | None = None
    unit_price_unit: str | None = None
    original: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CoverageResult:
    store_id: str
    postal_code: str
    status: str
    available: bool | None
    reason: str
    checked_at: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterResult:
    adapter_id: str
    coverage: CoverageResult
    observations: list[PriceObservation] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
