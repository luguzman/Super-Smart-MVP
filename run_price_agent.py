#!/usr/bin/env python3
"""CLI de la primera fase del Price Intelligence Agent."""
from __future__ import annotations

import argparse
from pathlib import Path

from price_agent.orchestration import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera salidas trazables sin consultar fuentes online.")
    parser.add_argument("--postal-code", required=True)
    parser.add_argument("--product-id", action="append", dest="product_ids")
    parser.add_argument("--product-limit", type=int)
    parser.add_argument("--input-csv", type=Path)
    parser.add_argument(
        "--mercadona-fixture",
        type=Path,
        help="Fixture JSON local de Mercadona; no realiza peticiones de red.",
    )
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.json"))
    parser.add_argument("--registry", type=Path, default=Path("data/supermarkets_registry.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/imports"))
    args = parser.parse_args()
    try:
        paths = run(
            catalog_path=args.catalog,
            registry_path=args.registry,
            output_dir=args.output_dir,
            postal_code=args.postal_code,
            product_ids=args.product_ids,
            product_limit=args.product_limit,
            input_csv=args.input_csv,
            mercadona_fixture_path=args.mercadona_fixture,
        )
    except (OSError, ValueError) as error:
        raise SystemExit(f"Ejecución cancelada: {error}")
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
