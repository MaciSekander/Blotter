import unittest

import pandas as pd

from bloomberg_provider import normalize_snapshot


class BloombergProviderTest(unittest.TestCase):
    def test_normalizes_long_snapshot(self):
        raw = pd.DataFrame(
            [
                {"ticker": "TY U6", "field": "LAST_PRICE", "value": "109.25"},
                {"ticker": "US U6", "field": "PX_LAST", "value": 111.5},
                {"ticker": "SKIP", "field": "BID", "value": 1.0},
            ]
        )

        out = normalize_snapshot(raw)

        self.assertEqual(out["ticker"].tolist(), ["TY U6", "US U6"])
        self.assertEqual(out["last_price"].tolist(), [109.25, 111.5])
        self.assertIn("time", out.columns)

    def test_normalizes_wide_snapshot(self):
        raw = pd.DataFrame({"last_price": [4.25, 4.5]}, index=["SR 5Y", "SR 10Y"])

        out = normalize_snapshot(raw)

        self.assertEqual(out["ticker"].tolist(), ["SR 5Y", "SR 10Y"])
        self.assertEqual(out["last_price"].tolist(), [4.25, 4.5])


if __name__ == "__main__":
    unittest.main()
