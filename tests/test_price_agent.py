import csv
import json
import tempfile
import unittest
from pathlib import Path

from price_agent.adapters import ManualCsvAdapter
from price_agent.matching import match_products
from price_agent.models import NormalizedProduct, PriceObservation
from price_agent.normalization import normalize_catalog_product, normalize_ean
from price_agent.orchestration import run
from price_agent.registry import SupermarketRegistry
from price_agent.validation import ValidationError, validate_observations, validate_postal_code


ROOT = Path(__file__).parents[1]


class NormalizationTests(unittest.TestCase):
    def test_normalizes_spreadsheet_ean_and_weight(self):
        product = normalize_catalog_product({
            "id": "P1", "name": "  Leche   entera ", "brand": "Marca",
            "ean": "8412345678901.0", "category": "Lácteos", "weight_g": 1000,
        })
        self.assertEqual(product.ean, "8412345678901")
        self.assertEqual(product.amount, 1)
        self.assertEqual(product.unit, "kg")
        self.assertEqual(product.name, "Leche entera")

    def test_rejects_ambiguous_ean(self):
        self.assertEqual(normalize_ean("ABC-123"), "")


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.expected = NormalizedProduct("P1", "Arroz largo", "Marca", "8412345678901", "Arroz", 1, "kg")

    def test_ean_is_level_one_and_auto_importable(self):
        candidate = NormalizedProduct("X", "Otro texto", "Otra", "8412345678901", "Otro", 2, "kg")
        self.assertEqual(match_products(self.expected, candidate).level, 1)
        self.assertTrue(match_products(self.expected, candidate).auto_import)

    def test_same_brand_name_format_is_level_two(self):
        candidate = NormalizedProduct("X", "arroz largo", "marca", "", "Arroz", 1, "kg")
        result = match_products(self.expected, candidate)
        self.assertEqual(result.level, 2)
        self.assertTrue(result.auto_import)

    def test_equivalent_never_auto_imports(self):
        candidate = NormalizedProduct("X", "Arroz redondo", "Otra", "", "Arroz", 1, "kg")
        result = match_products(self.expected, candidate)
        self.assertEqual(result.level, 4)
        self.assertFalse(result.auto_import)


class ValidationTests(unittest.TestCase):
    def test_rejects_unknown_product(self):
        row = PriceObservation("NO_EXISTE", "BM", 2.0, "2026-10-02")
        with self.assertRaisesRegex(ValidationError, "desconocido"):
            validate_observations([row], {"P001"})

    def test_validates_spanish_postal_code(self):
        self.assertEqual(validate_postal_code("28002"), "28002")
        with self.assertRaises(ValidationError):
            validate_postal_code("99999")


class RegistryAndAdapterTests(unittest.TestCase):
    def test_registry_loads_national_and_regional_chains(self):
        registry = SupermarketRegistry.load(ROOT / "data/supermarkets_registry.json")
        self.assertGreaterEqual(len(registry.list()), 20)
        self.assertEqual(registry.get("mercadona")["adapter_status"], "manual")
        self.assertEqual(registry.get("gadis")["geographic_scope"], "regional")

    def test_manual_adapter_keeps_multiple_stores(self):
        adapter = ManualCsvAdapter(ROOT / "tests/fixtures/manual_prices.csv", {"P001", "P002"})
        product = NormalizedProduct("P001", "Producto", amount=0.5, unit="kg")
        result = adapter.collect([product], "28002")
        self.assertEqual(len(result.observations), 2)
        self.assertEqual(result.observations[0].unit_price_eur, 7.0)
        self.assertTrue(all(item.postal_code == "28002" for item in result.observations))

    def test_manual_adapter_does_not_mix_postal_codes(self):
        with tempfile.TemporaryDirectory() as temporary:
            csv_path = Path(temporary) / "prices.csv"
            csv_path.write_text(
                "product_id,store,price_eur,observed_on,postal_code\n"
                "P001,BM,3.00,2026-10-02,28002\n"
                "P001,BM,1.00,2026-10-02,08001\n",
                encoding="utf-8",
            )
            adapter = ManualCsvAdapter(csv_path, {"P001"})
            result = adapter.collect([NormalizedProduct("P001", "Producto")], "28002")
        self.assertEqual(len(result.observations), 1)
        self.assertEqual(result.observations[0].price_eur, 3.0)
        self.assertEqual(result.observations[0].postal_code, "28002")

    def test_runner_targets_products_and_generates_four_compatible_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = run(
                catalog_path=ROOT / "data/catalog.json",
                registry_path=ROOT / "data/supermarkets_registry.json",
                output_dir=Path(temporary),
                postal_code="28002",
                product_ids=["P001"],
                input_csv=ROOT / "tests/fixtures/manual_prices.csv",
            )
            self.assertEqual(set(paths), {"prices", "review", "pending_equivalences", "coverage"})
            with paths["prices"].open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(set(rows[0]), {
                "product_id", "store", "price_eur", "observed_on", "promotion_eur",
                "loyalty_required", "source_url", "notes", "postal_code",
            })
            self.assertTrue(all(row["postal_code"] == "28002" for row in rows))
            coverage = json.loads(paths["coverage"].read_text(encoding="utf-8"))
            self.assertEqual(coverage["requested_products"], 1)
            self.assertEqual(coverage["observations"], 2)
            self.assertGreaterEqual(len(coverage["chains"]), 21)
            mercadona = next(row for row in coverage["chains"] if row["store_id"] == "mercadona")
            self.assertIsNone(mercadona["available"])


if __name__ == "__main__":
    unittest.main()
