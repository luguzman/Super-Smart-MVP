"""Adaptadores disponibles en la fase inicial."""

from .base import SupermarketAdapter
from .manual_csv import ManualCsvAdapter
from .mercadona_fixture import MercadonaFixtureAdapter, MercadonaFixtureError

__all__ = [
    "ManualCsvAdapter",
    "MercadonaFixtureAdapter",
    "MercadonaFixtureError",
    "SupermarketAdapter",
]
