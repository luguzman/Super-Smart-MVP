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

    def test_uses_only_requested_postal_code(self):
        catalog = [{"id": "P001", "name": "Tomate pera", "brand": "", "category": "Verdura", "weight_g": 1000, "ean": "", "name_tokens": ["tomate", "pera"]}]
        scoped = [
            {"product_id": "P001", "store": "BM", "price_eur": 4, "source": "importacion_csv", "observed_on": "2026-10-02", "postal_code": "28002"},
            {"product_id": "P001", "store": "BM", "price_eur": 1, "source": "importacion_csv", "observed_on": "2026-10-03", "postal_code": "08001"},
        ]
        with patch("app.load_json", side_effect=[catalog, [], scoped]):
            result = app.optimize({"items": [{"product_id": "P001", "quantity": 1}], "postal_code": "28002"})
        self.assertEqual(result["plan"]["total"], 4)

    def test_uses_legacy_observation_as_postal_fallback(self):
        catalog = [{"id": "P001", "name": "Tomate pera", "brand": "", "category": "Verdura", "weight_g": 1000, "ean": "", "name_tokens": ["tomate", "pera"]}]
        legacy = [{"product_id": "P001", "store": "BM", "price_eur": 2.5, "source": "catalogo_historico", "observed_on": None}]
        with patch("app.load_json", side_effect=[catalog, legacy, []]):
            result = app.optimize({"items": [{"product_id": "P001", "quantity": 1}], "postal_code": "28002"})
        self.assertEqual(result["plan"]["total"], 2.5)

    def test_rejects_invalid_postal_code(self):
        result = app.optimize({"items": [], "postal_code": "99999"})
        self.assertIsNone(result["plan"])
        self.assertEqual(result["message"], "Código postal no válido.")
