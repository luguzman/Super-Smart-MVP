"""Orquestación acotada a los productos objetivo."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from price_agent.adapters import ManualCsvAdapter, MercadonaFixtureAdapter
from price_agent.models import AdapterResult, CoverageResult
from price_agent.normalization import normalize_catalog_product
from price_agent.reports import write_reports
from price_agent.validation import validate_observations, validate_postal_code


def run(
    catalog_path: Path,
    registry_path: Path,
    output_dir: Path,
    postal_code: str,
    product_ids: list[str] | None = None,
    product_limit: int | None = None,
    input_csv: Path | None = None,
    mercadona_fixture_path: Path | None = None,
) -> dict[str, Path]:
    postal_code = validate_postal_code(postal_code)
    catalog_rows = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog = {row["id"]: normalize_catalog_product(row) for row in catalog_rows}
    requested = product_ids or list(catalog)
    unknown = sorted(set(requested) - set(catalog))
    if unknown:
        raise ValueError(f"product_id fuera del catálogo: {', '.join(unknown)}")
    if product_limit is not None:
        if product_limit <= 0:
            raise ValueError("product_limit debe ser positivo.")
        requested = requested[:product_limit]

    # Se valida el registro aun cuando esta fase solo ejecute la fuente manual.
    from price_agent.registry import SupermarketRegistry
    registry = SupermarketRegistry.load(registry_path)

    results = []
    if input_csv:
        adapter = ManualCsvAdapter(input_csv, set(catalog))
        results.append(adapter.collect((catalog[item] for item in requested), postal_code))
    if mercadona_fixture_path:
        adapter = MercadonaFixtureAdapter(mercadona_fixture_path, set(catalog))
        results.append(adapter.collect((catalog[item] for item in requested), postal_code))
    checked_at = datetime.now(timezone.utc).isoformat()
    executed_adapters = {result.adapter_id for result in results}
    for entry in registry.list():
        if entry["id"] in executed_adapters:
            continue
        coverage_status = entry["postal_coverage"]["status"]
        results.append(AdapterResult(
            adapter_id=entry["id"],
            coverage=CoverageResult(
                store_id=entry["id"],
                postal_code=postal_code,
                status=entry["adapter_status"],
                available=None,
                reason=(
                    "Cobertura por código postal no verificada; solo carga manual disponible."
                    if coverage_status == "unknown"
                    else f"Cobertura declarada en registro: {coverage_status}."
                ),
                checked_at=checked_at,
            ),
        ))
    observations = [item for result in results for item in result.observations]
    validate_observations(observations, set(catalog))
    return write_reports(output_dir, postal_code, date.today().isoformat(), results, requested)
