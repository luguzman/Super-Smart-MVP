#!/usr/bin/env python3
"""Valida e importa observaciones de precios desde CSV.

Formato obligatorio: product_id, store, price_eur, observed_on.
Campos opcionales: promotion_eur, loyalty_required, source_url, notes.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import date
from pathlib import Path


REQUIRED_COLUMNS = {"product_id", "store", "price_eur", "observed_on"}
OPTIONAL_COLUMNS = {"promotion_eur", "loyalty_required", "source_url", "notes"}


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


def parse_price_csv(csv_text: str, product_ids: set[str]):
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
        observations.append({
            "product_id": product_id,
            "store": store,
            "price_eur": price,
            "observed_on": observed_on,
            "promotion_eur": promotion,
            "loyalty_required": as_bool(row.get("loyalty_required"), row_number),
            "source_url": (row.get("source_url") or "").strip(),
            "notes": (row.get("notes") or "").strip(),
            "source": "importacion_csv",
            "confidence": "alta" if (row.get("source_url") or "").strip() else "media",
        })
    if not observations:
        raise PriceImportError("El CSV no contiene observaciones de precio.")
    return observations


def merge_observations(existing, incoming):
    """Reemplaza solo la misma observación diaria producto-tienda, sin borrar historia."""
    incoming_keys = {(row["product_id"], row["store"].lower(), row["observed_on"]) for row in incoming}
    retained = [
        row for row in existing
        if (row.get("product_id"), str(row.get("store", "")).lower(), row.get("observed_on")) not in incoming_keys
    ]
    for index, row in enumerate(incoming, start=1):
        row = dict(row)
        row["id"] = f"csv-{row['observed_on']}-{index}"
        retained.append(row)
    return retained


def import_csv_text(csv_text: str, catalog_path: Path, target_path: Path):
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    incoming = parse_price_csv(csv_text, {product["id"] for product in catalog})
    existing = json.loads(target_path.read_text(encoding="utf-8")) if target_path.exists() else []
    merged = merge_observations(existing, incoming)
    target_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return incoming


def main():
    parser = argparse.ArgumentParser(description="Importa precios recientes en el MVP.")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.json"))
    parser.add_argument("--output", type=Path, default=Path("data/local_price_observations.json"))
    args = parser.parse_args()
    try:
        imported = import_csv_text(args.csv_file.read_text(encoding="utf-8"), args.catalog, args.output)
    except PriceImportError as error:
        raise SystemExit(f"Importación cancelada: {error}")
    print(f"Importadas {len(imported)} observaciones en {args.output}.")


_parse_price_csv_without_fixture_guard = parse_price_csv


def parse_price_csv(*args, **kwargs):
    """Preserva el parser existente y bloquea fuentes sintéticas de fixture."""
    rows = _parse_price_csv_without_fixture_guard(*args, **kwargs)
    for row in rows:
        source_url = str(row.get("source_url", "")).strip()
        if source_url.lower().startswith("fixture://"):
            raise PriceImportError(
                "Los fixtures solo sirven para pruebas y no se pueden importar "
                "al historial del MVP."
            )
    return rows


if __name__ == "__main__":
    main()
