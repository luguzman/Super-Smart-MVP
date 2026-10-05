"""Escritura atómica de las cuatro salidas del agente."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from price_agent.models import AdapterResult


CSV_FIELDS = [
    "product_id", "store", "price_eur", "observed_on", "promotion_eur",
    "loyalty_required", "source_url", "notes",
]


def _write_json(path: Path, payload) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_reports(
    output_dir: Path,
    postal_code: str,
    run_date: str,
    results: list[AdapterResult],
    requested_ids: list[str],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"{postal_code}_{run_date}"
    paths = {
        "prices": output_dir / f"precios_{suffix}.csv",
        "review": output_dir / f"revision_{suffix}.md",
        "pending_equivalences": output_dir / f"equivalencias_pendientes_{suffix}.json",
        "coverage": output_dir / f"cobertura_{suffix}.json",
    }
    observations = [item for result in results for item in result.observations]
    temporary_csv = paths["prices"].with_suffix(".csv.tmp")
    with temporary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for item in observations:
            row = asdict(item)
            writer.writerow({field: row[field] for field in CSV_FIELDS})
    temporary_csv.replace(paths["prices"])

    coverage = {
        "postal_code": postal_code,
        "generated_on": run_date,
        "requested_products": len(requested_ids),
        "observations": len(observations),
        "chains": [result.coverage.as_dict() for result in results],
        "errors": [error for result in results for error in result.errors],
    }
    _write_json(paths["coverage"], coverage)
    _write_json(paths["pending_equivalences"], [])

    found = {item.product_id for item in observations}
    missing = [product_id for product_id in requested_ids if product_id not in found]
    available = [result.adapter_id for result in results if result.coverage.available is True]
    unavailable = [result.adapter_id for result in results if result.coverage.available is not True]
    review = [
        f"# Revisión de precios {postal_code} - {run_date}", "",
        "## Hechos observados", "",
        f"- Productos solicitados: {len(requested_ids)}",
        f"- Productos con observación: {len(found)}",
        f"- Cadenas/fuentes disponibles: {', '.join(available) or 'ninguna'}",
        f"- Cadenas/fuentes no disponibles o no verificadas: {', '.join(unavailable) or 'ninguna'}",
        "", "## Pendientes de revisión humana", "",
        f"- Productos no encontrados: {', '.join(missing) or 'ninguno'}",
        "- Equivalencias propuestas: ninguna; el adaptador manual solo acepta product_id del catálogo.",
        "- Promociones personales: no se procesan.",
        "", "## Inferencias y límites", "",
        "- La cobertura del CSV es declarada por el usuario y no implica cobertura comercial por código postal.",
        "- No se realizaron accesos de red, scraping, login, carrito ni compra.",
        "- Las filas sin URL conservan confianza media y deben contrastarse antes de comprar.",
    ]
    paths["review"].write_text("\n".join(review) + "\n", encoding="utf-8")
    return paths
