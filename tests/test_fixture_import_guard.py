import tempfile
import unittest
from pathlib import Path

from import_prices import PriceImportError, import_csv_text, parse_price_csv


FIXTURE_CSV = (
    "product_id,store,price_eur,observed_on,promotion_eur,loyalty_required,source_url,notes\n"
    "P001,Mercadona,3.99,2026-10-02,0.20,false,fixture://mercadona/P001,fixture local\n"
)
ERROR_MESSAGE = (
    "Los fixtures solo sirven para pruebas y no se pueden importar al historial del MVP"
)


class FixtureImportGuardTests(unittest.TestCase):
    def test_parse_price_csv_rejects_fixture_source_url(self):
        with self.assertRaisesRegex(PriceImportError, ERROR_MESSAGE):
            parse_price_csv(FIXTURE_CSV, {"P001"})

    def test_import_csv_text_rejects_fixture_source_url(self):
        catalog_path = Path("data/catalog.json")

        with tempfile.TemporaryDirectory() as tmp_dir:
            target_path = Path(tmp_dir) / "price_observations.json"
            target_path.write_text("[]\n", encoding="utf-8")

            with self.assertRaisesRegex(PriceImportError, ERROR_MESSAGE):
                import_csv_text(FIXTURE_CSV, catalog_path, target_path)

            self.assertEqual(target_path.read_text(encoding="utf-8"), "[]\n")


if __name__ == "__main__":
    unittest.main()
