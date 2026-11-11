import unittest

from app import create_app
from app.services.calculator import calculate_trade


class CalculatorTests(unittest.TestCase):
    def setUp(self):
        self.trade = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "balance": 10000,
            "risk_value": 1,
            "risk_mode": "percent",
            "entry": 1.085,
            "stop_loss": 1.08,
            "tp_method": "rr",
            "rr": 2,
        }

    def test_forex_percent_risk_and_rr_target(self):
        result = calculate_trade(self.trade)
        self.assertEqual(result["planned_risk"], 100)
        self.assertEqual(result["volume"], 0.2)
        self.assertAlmostEqual(result["take_profit"], 1.095)
        self.assertAlmostEqual(result["gross_profit"], 200)

    def test_sell_and_manual_target(self):
        trade = {**self.trade, "direction": "SELL", "entry": 1.085, "stop_loss": 1.09,
                 "tp_method": "price", "take_profit": 1.07}
        result = calculate_trade(trade)
        self.assertAlmostEqual(result["rr"], 3)
        self.assertAlmostEqual(result["take_profit"], 1.07)
        self.assertAlmostEqual(result["gross_profit"], 300)

    def test_gold_reference_contract_size_calculation(self):
        trade = {
            **self.trade,
            "symbol": "XAUUSD",
            "entry": 2400,
            "stop_loss": 2395,
        }
        result = calculate_trade(trade)
        self.assertEqual(result["volume"], 0.2)
        self.assertEqual(result["actual_risk"], 100)
        self.assertEqual(result["take_profit"], 2410)
        self.assertEqual(result["gross_profit"], 200)
        self.assertIn("FundedNext", result["profile_disclosure"])

    def test_fixed_cash_risk(self):
        result = calculate_trade({**self.trade, "risk_mode": "cash", "risk_value": 50})
        self.assertEqual(result["planned_risk"], 50)
        self.assertEqual(result["volume"], 0.1)

    def test_volume_rounds_down(self):
        result = calculate_trade({**self.trade, "risk_value": 1.27})
        self.assertEqual(result["volume"], 0.25)
        self.assertLessEqual(result["actual_risk"], result["planned_risk"])
        self.assertTrue(result["warnings"])

    def test_minimum_volume_is_disclosed(self):
        result = calculate_trade({**self.trade, "risk_value": 0.001})
        self.assertEqual(result["volume"], 0.01)
        self.assertGreater(result["actual_risk"], result["planned_risk"])
        self.assertTrue(result["warnings"])

    def test_invalid_inputs(self):
        invalid_cases = [
            ({**self.trade, "balance": 0}, "balance"),
            ({**self.trade, "risk_value": 101}, "100%"),
            ({**self.trade, "stop_loss": 1.09}, "stop loss"),
            ({**self.trade, "tp_method": "price", "take_profit": 1.08}, "take profit"),
            ({**self.trade, "entry": float("inf")}, "entry price"),
        ]
        for data, message in invalid_cases:
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, message):
                calculate_trade(data)

    def test_unavailable_profile_does_not_guess(self):
        for symbol in ("EURGBP", "BTCUSD", "XAGUSD", "NAS100", "USOIL"):
            with self.subTest(symbol=symbol), self.assertRaisesRegex(ValueError, "No lot size was calculated"):
                calculate_trade({**self.trade, "symbol": symbol})

    def test_usd_base_pair_uses_entry_price_conversion(self):
        trade = {**self.trade, "symbol": "USDJPY", "entry": 150, "stop_loss": 149.5}
        result = calculate_trade(trade)
        self.assertAlmostEqual(result["volume"], 0.3)
        self.assertAlmostEqual(result["actual_risk"], 100)

    def test_api_returns_clear_validation(self):
        client = create_app({"TESTING": True}).test_client()
        response = client.post("/api/calculate", json={**self.trade, "balance": -1})
        self.assertEqual(response.status_code, 400)
        self.assertIn("balance", response.get_json()["error"])

    def test_catalogue_counts_and_required_symbols(self):
        client = create_app({"TESTING": True}).test_client()
        catalogue = client.get("/api/instruments").get_json()["instruments"]
        symbols = {item["symbol"] for item in catalogue}
        self.assertGreaterEqual(sum(item["category"] == "Forex" for item in catalogue), 28)
        self.assertTrue({"BTCUSD", "ETHUSD", "XAUUSD", "XAGUSD", "NAS100", "USOIL"} <= symbols)


if __name__ == "__main__":
    unittest.main()
