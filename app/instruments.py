"""Data-driven instrument catalogue and explicitly scoped reference profiles."""

FX_NAMES = {
    "EURUSD": "Euro / US Dollar", "GBPUSD": "British Pound / US Dollar",
    "AUDUSD": "Australian Dollar / US Dollar", "NZDUSD": "New Zealand Dollar / US Dollar",
    "USDJPY": "US Dollar / Japanese Yen", "USDCAD": "US Dollar / Canadian Dollar",
    "USDCHF": "US Dollar / Swiss Franc", "EURGBP": "Euro / British Pound",
    "EURJPY": "Euro / Japanese Yen", "EURCHF": "Euro / Swiss Franc",
    "EURAUD": "Euro / Australian Dollar", "EURNZD": "Euro / New Zealand Dollar",
    "EURCAD": "Euro / Canadian Dollar", "GBPJPY": "British Pound / Japanese Yen",
    "GBPCHF": "British Pound / Swiss Franc", "GBPAUD": "British Pound / Australian Dollar",
    "GBPCAD": "British Pound / Canadian Dollar", "GBPNZD": "British Pound / New Zealand Dollar",
    "AUDJPY": "Australian Dollar / Japanese Yen", "AUDCAD": "Australian Dollar / Canadian Dollar",
    "AUDCHF": "Australian Dollar / Swiss Franc", "AUDNZD": "Australian Dollar / New Zealand Dollar",
    "NZDJPY": "New Zealand Dollar / Japanese Yen", "NZDCAD": "New Zealand Dollar / Canadian Dollar",
    "NZDCHF": "New Zealand Dollar / Swiss Franc", "CADJPY": "Canadian Dollar / Japanese Yen",
    "CADCHF": "Canadian Dollar / Swiss Franc", "CHFJPY": "Swiss Franc / Japanese Yen",
    "USDZAR": "US Dollar / South African Rand", "USDMXN": "US Dollar / Mexican Peso",
    "USDTRY": "US Dollar / Turkish Lira", "USDSEK": "US Dollar / Swedish Krona",
    "USDNOK": "US Dollar / Norwegian Krone", "USDPLN": "US Dollar / Polish Zloty",
    "USDHUF": "US Dollar / Hungarian Forint", "USDSGD": "US Dollar / Singapore Dollar",
    "USDHKD": "US Dollar / Hong Kong Dollar",
}

OTHER_INSTRUMENTS = [
    ("BTCUSD", "Bitcoin / US Dollar", "Crypto"),
    ("ETHUSD", "Ether / US Dollar", "Crypto"),
    ("LTCUSD", "Litecoin / US Dollar", "Crypto"),
    ("XRPUSD", "XRP / US Dollar", "Crypto"),
    ("XAUUSD", "Gold / US Dollar", "Metals"),
    ("XAGUSD", "Silver / US Dollar", "Metals"),
    ("US30", "US Wall Street 30", "Indices"),
    ("NAS100", "US Tech 100", "Indices"),
    ("SPX500", "US 500", "Indices"),
    ("GER40", "Germany 40", "Indices"),
    ("UK100", "UK 100", "Indices"),
    ("JP225", "Japan 225", "Indices"),
    ("USOIL", "US Crude Oil", "Energies"),
    ("UKOIL", "UK Brent Oil", "Energies"),
    ("XNGUSD", "Natural Gas / US Dollar", "Energies"),
]


def _fx_profile(symbol):
    base, quote = symbol[:3], symbol[3:]
    # The 100,000-unit lot is a common FX reference convention, not a
    # specification for any particular broker or trading account.
    usable = quote == "USD" or base == "USD"
    return {
        "symbol": symbol,
        "name": FX_NAMES[symbol],
        "category": "Forex",
        "calculation_status": "reference_estimate" if usable else "unavailable",
        "base_currency": base,
        "quote_currency": quote,
        "contract_size": 100000 if usable else None,
        "profit_currency": quote,
        "minimum_volume": 0.01 if usable else None,
        "maximum_volume": 100 if usable else None,
        "volume_step": 0.01 if usable else None,
        "price_precision": 3 if "JPY" in symbol else 5,
        "conversion_method": "entry_inverse" if base == "USD" and quote != "USD" else "identity",
        "source_note": (
            "Uses the common 100,000-base-unit FX lot convention. "
            + (
                "USD quote-currency value is converted at the entered entry price. "
                if base == "USD" and quote != "USD" else
                "The quote currency is USD. "
            )
                + "Uses provisional 0.01 minimum/step and 100-lot maximum constraints. "
                + "Reference estimate only; not verified against a broker."
            if usable else
            "Requires a current conversion rate from the quote currency to USD. "
            "No live conversion feed or independently verified reference rate is configured."
        ),
    }


def get_instruments():
    instruments = [_fx_profile(symbol) for symbol in FX_NAMES]
    instruments.extend({
        "symbol": symbol,
        "name": name,
        "category": category,
        "calculation_status": "reference_estimate" if symbol == "XAUUSD" else "unavailable",
        "base_currency": None,
        "quote_currency": "USD",
        "contract_size": 100 if symbol == "XAUUSD" else None,
        "profit_currency": "USD",
        "minimum_volume": 0.01 if symbol == "XAUUSD" else None,
        "maximum_volume": 100 if symbol == "XAUUSD" else None,
        "volume_step": 0.01 if symbol == "XAUUSD" else None,
        "price_precision": 2,
        "conversion_method": "identity",
        "source_note": (
            "Gold reference contract size: 100 units per lot, as documented by "
            "FundedNext for commodities (their article says this applies to all accounts). "
            "The 0.01 minimum/step and 100-lot maximum are generic calculator assumptions, "
            "not specified in that source. This is a reference estimate, not a broker quote."
            if symbol == "XAUUSD" else
            "Contract size, tick value and volume constraints vary by product and "
            "provider. No reliable, product-specific reference profile is configured."
        ),
    } for symbol, name, category in OTHER_INSTRUMENTS)
    return instruments


INSTRUMENTS = {item["symbol"]: item for item in get_instruments()}
