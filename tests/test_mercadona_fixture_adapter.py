import csv
import json
import tempfile
import unittest
from pathlib import Path

from price_agent.adapters import MercadonaFixtureAdapter, MercadonaFixtureError
from price_agent.models import NormalizedProduct
from price_agent.orchestration import run


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests/fixtures/mercadona_prices.json"
CATALOG_IDS = {"P001", "P002"}


class MercadonaFixtureAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = MercadonaFixtureAdapter(FIXTURE, CATALOG_IDS)
        self.p001 = NormalizedProduct("P001", "Guacamole", amount=0.5, unit="kg")

    def test_discovers_supported_coverage(self):
        coverage = self.adapter.discover_coverage("28002")
        self.assertTrue(coverage.available)
        self.assertEqual(coverage.status, "fixture")
        self.assertIn("no verificada por red", coverage.reason)

    def test_reports_unsupported_coverage(self):
        coverage = self.adapter.discover_coverage("08001")
        self.assertFalse(coverage.available)
        self.assertIn("no declara cobertura", coverage.reason)

    def test_searches_only_requested_product(self):
        matches = self.adapter.search_product(self.p001, "28002")
        self.assertEqual([item.product_id for item in matches], ["P001"])
        self.assertEqual(self.adapter.search_product(NormalizedProduct("P003", "Otro"), "28002"), [])

    def test_returns_product_details_by_fixture_url(self):
        product = self.adapter.get_product_details("fixture://mercadona/P001", "28002")
        self.assertEqual(product.ean, "8480000038401")
        self.assertEqual(product.brand, "Hacendado Fresh")
        self.assertIsNone(self.adapter.get_product_details("fixture://mercadona/no-existe", "28002"))

    def test_builds_traceable_price_observation(self):
        observation = self.adapter.get_price(self.p001, "28002")
        self.assertEqual(observation.price_eur, 3.99)
        self.assertEqual(observation.promotion_eur, 0.2)
        self.assertEqual(observation.observed_on, "2026-10-02")
        self.assertEqual(observation.source, "mercadona_fixture")
        self.assertEqual(observation.source_url, "fixture://mercadona/P001")
        self.assertEqual(observation.availability, "available")
        self.assertEqual(observation.confidence, "high")
        self.assertEqual(observation.unit_price_eur, 7.98)

    def test_collects_only_requested_products_and_marks_missing(self):
        missing = NormalizedProduct("P003", "No incluido")
        result = self.adapter.collect([self.p001, missing], "28002")
        self.assertEqual([item.product_id for item in result.observations], ["P001"])
        self.assertEqual(result.not_found, ["P003"])
        self.assertEqual(result.errors, [])

    def test_rejects_fixture_product_outside_catalog(self):
        path = ROOT / "tests/fixtures/mercadona_unknown_product.json"
        with self.assertRaisesRegex(MercadonaFixtureError, "fuera del catálogo"):
            MercadonaFixtureAdapter(path, CATALOG_IDS)

    def test_runner_includes_fixture_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = run(
                catalog_path=ROOT / "data/catalog.json",
                registry_path=ROOT / "data/supermarkets_registry.json",
                output_dir=Path(temporary),
                postal_code="28002",
                product_ids=["P001"],
                mercadona_fixture_path=FIXTURE,
            )
            with paths["prices"].open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["product_id"], "P001")
            coverage = json.loads(paths["coverage"].read_text(encoding="utf-8"))
            mercadona = [item for item in coverage["chains"] if item["store_id"] == "mercadona"]
            self.assertEqual(len(mercadona), 1)
            self.assertTrue(mercadona[0]["available"])


if __name__ == "__main__":
    unittest.main()
