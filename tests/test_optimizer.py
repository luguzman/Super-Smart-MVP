import unittest
from unittest.mock import patch

import app


class OptimizerTests(unittest.TestCase):
    def test_prefers_newer_manual_price_over_historical_catalog_price(self):
        catalog = [{"id": "P001", "name": "Tomate pera", "brand": "", "category": "Verdura", "weight_g": 1000, "ean": "", "name_tokens": ["tomate", "pera"]}]
        historical = [{"product_id": "P001", "store": "BM", "price_eur": 1, "source": "catalogo_historico", "observed_on": None}]
        recent = [{"product_id": "P001", "store": "BM", "price_eur": 2, "source": "importacion_csv", "observed_on": "2026-10-02"}]
        with patch("app.load_json", side_effect=[catalog, historical, recent]):
            result = app.optimize({"items": [{"product_id": "P001", "quantity": 1}]})
        self.assertEqual(result["plan"]["total"], 2)
