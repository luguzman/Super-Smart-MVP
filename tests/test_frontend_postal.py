import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class FrontendPostalCodeTests(unittest.TestCase):
    def test_postal_code_is_editable_and_defaults_to_28002(self):
        html = (ROOT / "static/index.html").read_text(encoding="utf-8")
        self.assertIn('id="postal-code"', html)
        self.assertIn('value="28002"', html)
        self.assertIn('pattern="[0-9]{5}"', html)

    def test_frontend_sends_postal_code_to_price_endpoints(self):
        javascript = (ROOT / "static/app.js").read_text(encoding="utf-8")
        self.assertIn("const postalCode", javascript)
        self.assertEqual(javascript.count("postal_code: postalCode()"), 3)
        self.assertIn("'/api/plan'", javascript)
        self.assertIn("'/api/observations'", javascript)
        self.assertIn("'/api/import-prices'", javascript)


if __name__ == "__main__":
    unittest.main()
