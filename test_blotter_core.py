import unittest

from blotter_core import normalize_blotter, parse_treasury_price


class BlotterCoreTest(unittest.TestCase):
    def test_parse_treasury_price_handles_plus_and_eighths(self):
        self.assertAlmostEqual(parse_treasury_price("109-04+"), 109.140625)
        self.assertAlmostEqual(parse_treasury_price("98-181"), 98.56640625)

    def test_swaption_notional_is_scaled_to_dollars(self):
        df = normalize_blotter([["SR 15Y", -6.0, 4.272]])

        self.assertEqual(df.loc[0, "Instrument Type"], "Swaption")
        self.assertEqual(df.loc[0, "Input Unit"], "mm")
        self.assertEqual(df.loc[0, "Display Quantity"], "-6")
        self.assertEqual(df.loc[0, "Signed Notional"], -6_000_000)
        self.assertEqual(df.loc[0, "Display Notional"], "-$6.0mm")
        self.assertEqual(df.loc[0, "Display Quote"], "4.2720%")

    def test_futures_notional_uses_contract_multiplier(self):
        df = normalize_blotter([["TY U6", 25.0, "109-04+"]])

        self.assertEqual(df.loc[0, "Instrument Type"], "Treasury Future")
        self.assertEqual(df.loc[0, "Input Unit"], "contracts")
        self.assertEqual(df.loc[0, "Display Quantity"], "25")
        self.assertEqual(df.loc[0, "Signed Notional"], 2_500_000)
        self.assertEqual(df.loc[0, "Display Notional"], "$2.5mm")

    def test_treasury_bond_notional_uses_contract_multiplier(self):
        df = normalize_blotter([["USTB 3605_4.375", -25.0, "98-181"]])

        self.assertEqual(df.loc[0, "Instrument Type"], "Treasury Bond")
        self.assertEqual(df.loc[0, "Signed Notional"], -2_500_000)
        self.assertEqual(df.loc[0, "Display Notional"], "-$2.5mm")


if __name__ == "__main__":
    unittest.main()
