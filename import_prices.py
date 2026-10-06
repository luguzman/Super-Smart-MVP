#!/usr/bin/env python3
"""Valida e importa observaciones de precios desde CSV.

Formato obligatorio: product_id, store, price_eur, observed_on.
Campos opcionales: postal_code, promotion_eur, loyalty_required, source_url, notes.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import date
from pathlib import Path

from price_agent.validation import ValidationError, validate_postal_code


REQUIRED_COLUMNS = {"product_id", "store", "price_eur", "observed_on"}
OPTIONAL_COLUMNS = {"postal_code", "promotion_eur", "loyalty_required", "source_url", "notes"}


class PriceImportError(ValueError):
    pass


def decimal(value, field, row_number):
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise PriceImportError(f"Fila {row_number}: {field} debe ser un número.")


def as_bool(value, row_number):
    cleaned = str(value or "").strip().lower()
    if cleaned in {"", "0", "no", "false", "n"}:
        return False
    if cleaned in {"1", "si", "sí", "true", "s"}:
        return True
    raise PriceImportError(f"Fila {row_number}: loyalty_required debe ser sí/no.")


def parse_price_csv(
    csv_text: str,
    product_ids: set[str],
    default_postal_code: str = "",
):
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    columns = set(reader.fieldnames or [])
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise PriceImportError(f"Faltan columnas obligatorias: {', '.join(sorted(missing))}.")

    observations = []
    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        product_id = (row.get("product_id") or "").strip()
        store = (row.get("store") or "").strip()
        if product_id not in product_ids:
            raise PriceImportError(f"Fila {row_number}: product_id desconocido ({product_id}).")
        if not store:
            raise PriceImportError(f"Fila {row_number}: store es obligatorio.")
        price = decimal(row.get("price_eur"), "price_eur", row_number)
        promotion = decimal(row.get("promotion_eur") or 0, "promotion_eur", row_number)
        if price <= 0 or promotion < 0 or promotion >= price:
            raise PriceImportError(f"Fila {row_number}: revisa precio y descuento.")
        observed_on = (row.get("observed_on") or "").strip()
        try:
            date.fromisoformat(observed_on)
        except ValueError:
            raise PriceImportError(f"Fila {row_number}: observed_on debe usar AAAA-MM-DD.")
        postal_code = (row.get("postal_code") or default_postal_code or "").strip()
        if postal_code:
            try:
                postal_code = validate_postal_code(postal_code)
            except ValidationError as error:
                raise PriceImportError(
                    f"Fila {row_number}: postal_code debe ser un CP español válido de cinco dígitos."
                ) from error
        source_url = (row.get("source_url") or "").strip()
        if source_url.lower().startswith("fixture://"):
            raise PriceImportError(
                "Los fixtures solo sirven para pruebas y no se pueden importar "
                "al historial del MVP."
            )
        observations.append({
            "product_id": product_id,
            "store": store,
            "price_eur": price,
            "observed_on": observed_on,
            "postal_code": postal_code,
            "promotion_eur": promotion,
            "loyalty_required": as_bool(row.get("loyalty_required"), row_number),
            "source_url": source_url,
            "notes": (row.get("notes") or "").strip(),
            "source": "importacion_csv",
            "confidence": "alta" if source_url else "media",
        })
    if not observations:
        raise PriceImportError("El CSV no contiene observaciones de precio.")
    return observations


def merge_observations(existing, incoming):
    """Reemplaza solo la misma observación diaria producto-tienda-CP, sin borrar historia."""
    incoming_keys = {
        (row["product_id"], row["store"].lower(), row["observed_on"], row.get("postal_code", ""))
        for row in incoming
    }
    retained = [
        row for row in existing
        if (
            row.get("product_id"),
            str(row.get("store", "")).lower(),
            row.get("observed_on"),
            row.get("postal_code", ""),
        ) not in incoming_keys
    ]
    for index, row in enumerate(incoming, start=1):
        row = dict(row)
        row["id"] = f"csv-{row['observed_on']}-{index}"
        retained.append(row)
    return retained


def import_csv_text(
    csv_text: str,
    catalog_path: Path,
    target_path: Path,
    default_postal_code: str = "",
):
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    incoming = parse_price_csv(
        csv_text,
        {product["id"] for product in catalog},
        default_postal_code=default_postal_code,
    )
    existing = json.loads(target_path.read_text(encoding="utf-8")) if target_path.exists() else []
    merged = merge_observations(existing, incoming)
    target_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return incoming


def main():
    parser = argparse.ArgumentParser(description="Importa precios recientes en el MVP.")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.json"))
    parser.add_argument("--output", type=Path, default=Path("data/local_price_observations.json"))
    parser.add_argument("--postal-code", default="", help="CP para CSV legacy sin columna postal_code.")
    args = parser.parse_args()
    try:
        imported = import_csv_text(
            args.csv_file.read_text(encoding="utf-8"),
            args.catalog,
            args.output,
            default_postal_code=args.postal_code,
        )
    except PriceImportError as error:
        raise SystemExit(f"Importación cancelada: {error}")
    print(f"Importadas {len(imported)} observaciones en {args.output}.")

if __name__ == "__main__":
    main()
