import unittest

from import_prices import PriceImportError, merge_observations, parse_price_csv


class PriceImportTests(unittest.TestCase):
    def test_accepts_valid_csv(self):
        rows = parse_price_csv(
            "product_id,store,price_eur,observed_on,promotion_eur,loyalty_required\nP001,BM,3.20,2026-10-02,0.30,si\n",
            {"P001"},
        )
        self.assertEqual(rows[0]["price_eur"], 3.2)
        self.assertTrue(rows[0]["loyalty_required"])

    def test_rejects_unknown_product(self):
        with self.assertRaisesRegex(PriceImportError, "desconocido"):
            parse_price_csv("product_id,store,price_eur,observed_on\nP999,BM,2.20,2026-10-02\n", {"P001"})

    def test_replaces_same_product_store_and_day(self):
        existing = [{"product_id": "P001", "store": "BM", "observed_on": "2026-10-02", "price_eur": 4}]
        incoming = [{"product_id": "P001", "store": "BM", "observed_on": "2026-10-02", "price_eur": 3}]
        merged = merge_observations(existing, incoming)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["price_eur"], 3)

    def test_preserves_observations_for_different_postal_codes(self):
        existing = [{"product_id": "P001", "store": "BM", "observed_on": "2026-10-02", "postal_code": "28002", "price_eur": 4}]
        incoming = [{"product_id": "P001", "store": "BM", "observed_on": "2026-10-02", "postal_code": "08001", "price_eur": 3}]
        merged = merge_observations(existing, incoming)
        self.assertEqual(len(merged), 2)
        self.assertEqual({row["postal_code"] for row in merged}, {"28002", "08001"})

    def test_assigns_default_postal_code_to_legacy_csv(self):
        rows = parse_price_csv(
            "product_id,store,price_eur,observed_on\nP001,BM,3.20,2026-10-02\n",
            {"P001"},
            default_postal_code="28002",
        )
        self.assertEqual(rows[0]["postal_code"], "28002")

    def test_rejects_invalid_postal_code(self):
        with self.assertRaisesRegex(PriceImportError, "postal_code"):
            parse_price_csv(
                "product_id,store,price_eur,observed_on,postal_code\nP001,BM,3.20,2026-10-02,99999\n",
                {"P001"},
            )
