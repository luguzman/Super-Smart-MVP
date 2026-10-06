"""Adaptador determinista de Mercadona basado exclusivamente en fixtures locales."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from price_agent.adapters.base import SupermarketAdapter
from price_agent.models import CoverageResult, NormalizedProduct, PriceObservation


class MercadonaFixtureError(ValueError):
    pass


class MercadonaFixtureAdapter(SupermarketAdapter):
    """Lee observaciones locales sin realizar ninguna operación de red."""

    adapter_id = "mercadona"

    def __init__(self, fixture_path: Path, catalog_product_ids: set[str]):
        self.fixture_path = fixture_path
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if payload.get("store_id") != self.adapter_id:
            raise MercadonaFixtureError("El fixture debe declarar store_id=mercadona.")
        postal_codes = payload.get("postal_codes")
        products = payload.get("products")
        if not isinstance(postal_codes, list) or not all(isinstance(item, str) for item in postal_codes):
            raise MercadonaFixtureError("postal_codes debe ser una lista de textos.")
        if not isinstance(products, list):
            raise MercadonaFixtureError("products debe ser una lista.")
        self._postal_codes = set(postal_codes)
        self._rows: dict[str, dict] = {}
        self._by_url: dict[str, dict] = {}
        for index, row in enumerate(products, start=1):
            self._validate_row(row, index, catalog_product_ids)
            product_id = row["product_id"]
            source_url = row["source_url"]
            if product_id in self._rows:
                raise MercadonaFixtureError(f"Producto duplicado en fixture: {product_id}.")
            if source_url in self._by_url:
                raise MercadonaFixtureError(f"source_url duplicada en fixture: {source_url}.")
            self._rows[product_id] = dict(row)
            self._by_url[source_url] = dict(row)

    @staticmethod
    def _validate_row(row: dict, index: int, catalog_product_ids: set[str]) -> None:
        required = {"product_id", "name", "price_eur", "observed_on", "source_url"}
        if not isinstance(row, dict) or required - set(row):
            raise MercadonaFixtureError(f"Producto {index}: faltan campos obligatorios.")
        if row["product_id"] not in catalog_product_ids:
            raise MercadonaFixtureError(f"Producto {index}: product_id fuera del catálogo ({row['product_id']}).")
        try:
            price = float(row["price_eur"])
            promotion = float(row.get("promotion_eur", 0))
        except (TypeError, ValueError) as error:
            raise MercadonaFixtureError(f"Producto {index}: precio o promoción no numéricos.") from error
        if price <= 0 or promotion < 0 or promotion >= price:
            raise MercadonaFixtureError(f"Producto {index}: precio o promoción inválidos.")
        try:
            date.fromisoformat(row["observed_on"])
        except (TypeError, ValueError) as error:
            raise MercadonaFixtureError(f"Producto {index}: observed_on debe usar AAAA-MM-DD.") from error
        if not str(row["source_url"]).startswith("fixture://mercadona/"):
            raise MercadonaFixtureError(f"Producto {index}: source_url debe usar fixture://mercadona/.")
        if row.get("confidence", "high") not in {"low", "medium", "high"}:
            raise MercadonaFixtureError(f"Producto {index}: confidence no válida.")
        if row.get("availability", "available") not in {"available", "unavailable", "unknown"}:
            raise MercadonaFixtureError(f"Producto {index}: availability no válida.")
        if not isinstance(row.get("loyalty_required", False), bool):
            raise MercadonaFixtureError(f"Producto {index}: loyalty_required debe ser booleano.")
        amount = row.get("amount")
        if amount is not None:
            try:
                numeric_amount = float(amount)
            except (TypeError, ValueError) as error:
                raise MercadonaFixtureError(f"Producto {index}: amount debe ser positivo.") from error
            if numeric_amount <= 0 or not row.get("unit"):
                raise MercadonaFixtureError(f"Producto {index}: formato de unidad inválido.")

    def discover_coverage(self, postal_code: str) -> CoverageResult:
        available = postal_code in self._postal_codes
        return CoverageResult(
            store_id=self.adapter_id,
            postal_code=postal_code,
            status="fixture",
            available=available,
            reason=(
                "Cobertura declarada por fixture local; no verificada por red."
                if available
                else "El fixture local no declara cobertura para este código postal."
            ),
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

    def search_product(self, query: NormalizedProduct, postal_code: str) -> list[NormalizedProduct]:
        if postal_code not in self._postal_codes:
            return []
        row = self._rows.get(query.product_id)
        return [self._product(row)] if row else []

    def get_product_details(self, product_url: str, postal_code: str) -> NormalizedProduct | None:
        if postal_code not in self._postal_codes:
            return None
        row = self._by_url.get(product_url)
        return self._product(row) if row else None

    def get_price(self, product: NormalizedProduct, postal_code: str) -> PriceObservation | None:
        if postal_code not in self._postal_codes:
            return None
        row = self._rows.get(product.product_id)
        if not row:
            return None
        amount = row.get("amount")
        unit = row.get("unit")
        unit_price = round(float(row["price_eur"]) / float(amount), 4) if amount and unit else None
        return PriceObservation(
            product_id=row["product_id"],
            store="Mercadona",
            price_eur=float(row["price_eur"]),
            observed_on=row["observed_on"],
            promotion_eur=float(row.get("promotion_eur", 0)),
            loyalty_required=bool(row.get("loyalty_required", False)),
            source="mercadona_fixture",
            source_url=row["source_url"],
            notes=str(row.get("notes", "")),
            availability=str(row.get("availability", "available")),
            confidence=str(row.get("confidence", "high")),
            unit_price_eur=unit_price,
            unit_price_unit=unit if unit_price is not None else None,
            original=dict(row),
            postal_code=postal_code,
        )

    @staticmethod
    def _product(row: dict) -> NormalizedProduct:
        return NormalizedProduct(
            product_id=row["product_id"],
            name=str(row["name"]),
            brand=str(row.get("brand", "")),
            ean=str(row.get("ean", "")),
            category=str(row.get("category", "")),
            amount=float(row["amount"]) if row.get("amount") is not None else None,
            unit=row.get("unit"),
            original=dict(row),
        )
