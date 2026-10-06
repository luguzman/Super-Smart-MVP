"""Fallback universal que consume el mismo CSV que el MVP."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from import_prices import parse_price_csv
from price_agent.adapters.base import SupermarketAdapter
from price_agent.models import AdapterResult, CoverageResult, NormalizedProduct, PriceObservation


class ManualCsvAdapter(SupermarketAdapter):
    adapter_id = "manual_csv"

    def __init__(self, csv_path: Path, catalog_product_ids: set[str]):
        self.csv_path = csv_path
        rows = parse_price_csv(csv_path.read_text(encoding="utf-8"), catalog_product_ids)
        self._rows: dict[str, list[dict]] = {}
        for row in rows:
            self._rows.setdefault(row["product_id"], []).append(row)

    def discover_coverage(self, postal_code: str) -> CoverageResult:
        return CoverageResult(
            store_id=self.adapter_id,
            postal_code=postal_code,
            status="manual",
            available=True,
            reason="Cobertura declarada por el fichero aportado; no verificada por red.",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

    def search_product(self, query: NormalizedProduct, postal_code: str) -> list[NormalizedProduct]:
        return [query] if self._rows_for_postal_code(query.product_id, postal_code) else []

    def get_product_details(self, product_url: str, postal_code: str) -> NormalizedProduct | None:
        return None

    def get_price(self, product: NormalizedProduct, postal_code: str) -> PriceObservation | None:
        rows = self._rows_for_postal_code(product.product_id, postal_code)
        if not rows:
            return None
        return self._observation(rows[0], product, postal_code)

    def _rows_for_postal_code(self, product_id: str, postal_code: str) -> list[dict]:
        rows = self._rows.get(product_id, [])
        scoped = [row for row in rows if row.get("postal_code") == postal_code]
        scoped_stores = {str(row["store"]).casefold() for row in scoped}
        legacy = [
            row for row in rows
            if not row.get("postal_code") and str(row["store"]).casefold() not in scoped_stores
        ]
        return scoped + legacy

    def collect(self, products, postal_code: str) -> AdapterResult:
        coverage = self.discover_coverage(postal_code)
        result = AdapterResult(adapter_id=self.adapter_id, coverage=coverage)
        for product in products:
            rows = self._rows_for_postal_code(product.product_id, postal_code)
            if not rows:
                result.not_found.append(product.product_id)
                continue
            result.observations.extend(self._observation(row, product, postal_code) for row in rows)
        return result

    @staticmethod
    def _observation(row: dict, product: NormalizedProduct, postal_code: str) -> PriceObservation:
        amount = product.amount
        unit_price = round(row["price_eur"] / amount, 4) if amount and product.unit else None
        return PriceObservation(
            product_id=row["product_id"],
            store=row["store"],
            price_eur=row["price_eur"],
            observed_on=row["observed_on"],
            promotion_eur=row["promotion_eur"],
            loyalty_required=row["loyalty_required"],
            source="manual_csv",
            source_url=row["source_url"],
            notes=row["notes"],
            availability="available",
            confidence="high" if row["source_url"] else "medium",
            unit_price_eur=unit_price,
            unit_price_unit=product.unit if unit_price is not None else None,
            original=dict(row),
            postal_code=row.get("postal_code") or postal_code,
        )
