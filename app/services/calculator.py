from decimal import Decimal, ROUND_DOWN

from app.instruments import INSTRUMENTS


def _number(data, field, label):
    try:
        value = Decimal(str(data[field]))
    except (KeyError, TypeError, ValueError, ArithmeticError):
        raise ValueError(f"Enter a valid {label}.") from None
    if not value.is_finite():
        raise ValueError(f"Enter a valid {label}.")
    return value


def calculate_trade(data):
    symbol = str(data.get("symbol", "")).upper()
    instrument = INSTRUMENTS.get(symbol)
    if not instrument:
        raise ValueError("Select an instrument from the catalogue.")
    if instrument["calculation_status"] != "reference_estimate":
        raise ValueError(
            f"{symbol} is listed, but a defensible reference calculation profile "
            "is not configured. No lot size was calculated."
        )

    direction = str(data.get("direction", "")).upper()
    if direction not in ("BUY", "SELL"):
        raise ValueError("Choose BUY or SELL.")

    balance = _number(data, "balance", "account balance")
    risk_value = _number(data, "risk_value", "risk")
    entry = _number(data, "entry", "entry price")
    stop = _number(data, "stop_loss", "stop-loss price")
    if balance <= 0:
        raise ValueError("Account balance must be greater than zero.")
    if risk_value <= 0:
        raise ValueError("Risk must be greater than zero.")
    if entry <= 0 or stop <= 0:
        raise ValueError("Entry and stop-loss prices must be greater than zero.")

    risk_mode = data.get("risk_mode", "percent")
    if risk_mode == "percent":
        if risk_value > Decimal("100"):
            raise ValueError("Risk percentage cannot exceed 100%.")
        planned_risk = balance * risk_value / Decimal("100")
        risk_percent = risk_value
    elif risk_mode == "cash":
        planned_risk = risk_value
        risk_percent = risk_value / balance * Decimal("100")
        if planned_risk > balance:
            raise ValueError("Fixed cash risk cannot exceed the account balance.")
    else:
        raise ValueError("Choose percentage or fixed cash risk.")

    if (direction == "BUY" and stop >= entry) or (direction == "SELL" and stop <= entry):
        expected = "below" if direction == "BUY" else "above"
        raise ValueError(f"For a {direction}, stop loss must be {expected} the entry price.")
    stop_distance = abs(entry - stop)
    contract_size = Decimal(str(instrument["contract_size"]))
    conversion_factor = Decimal("1") / entry if instrument["conversion_method"] == "entry_inverse" else Decimal("1")
    one_lot_loss = stop_distance * contract_size * conversion_factor
    raw_volume = (
        planned_risk * entry / (stop_distance * contract_size)
        if instrument["conversion_method"] == "entry_inverse"
        else planned_risk / one_lot_loss
    )

    minimum = Decimal(str(instrument["minimum_volume"]))
    maximum = Decimal(str(instrument["maximum_volume"]))
    step = Decimal(str(instrument["volume_step"]))
    raw = raw_volume
    warnings = []
    if raw < minimum:
        volume = minimum
        warnings.append(
            "The calculated size is below the minimum reference volume. "
            "Minimum size is shown; its estimated risk may exceed your budget."
        )
    elif raw > maximum:
        volume = maximum
        warnings.append(
            "The calculated size exceeds the maximum reference volume and has been capped. "
            "The resulting risk may be below your budget."
        )
    else:
        steps = ((raw - minimum) / step).to_integral_value(rounding=ROUND_DOWN)
        volume = minimum + steps * step
        if volume < raw:
            warnings.append("Volume was rounded down to the reference step to avoid exceeding planned risk.")

    actual_volume = volume
    actual_risk = actual_volume * one_lot_loss

    tp_method = data.get("tp_method", "rr")
    if tp_method == "rr":
        rr = _number(data, "rr", "risk-to-reward ratio")
        if rr <= 0:
            raise ValueError("Risk-to-reward ratio must be greater than zero.")
        tp = entry + stop_distance * rr if direction == "BUY" else entry - stop_distance * rr
    elif tp_method == "price":
        tp = _number(data, "take_profit", "take-profit price")
        if tp <= 0:
            raise ValueError("Take-profit price must be greater than zero.")
        if (direction == "BUY" and tp <= entry) or (direction == "SELL" and tp >= entry):
            expected = "above" if direction == "BUY" else "below"
            raise ValueError(f"For a {direction}, take profit must be {expected} the entry price.")
        rr = abs(tp - entry) / stop_distance
    else:
        raise ValueError("Choose a take-profit method.")

    profit = abs(tp - entry) * contract_size * conversion_factor * actual_volume
    precision = instrument["price_precision"]
    return {
        "symbol": symbol,
        "name": instrument["name"],
        "category": instrument["category"],
        "direction": direction,
        "balance": float(balance),
        "risk_mode": risk_mode,
        "risk_value": float(risk_value),
        "planned_risk": float(planned_risk),
        "risk_percent": float(risk_percent),
        "entry": float(entry),
        "stop_loss": float(stop),
        "stop_distance": float(stop_distance),
        "take_profit": float(tp),
        "target_distance": float(abs(tp - entry)),
        "rr": float(rr),
        "volume": float(actual_volume),
        "actual_risk": float(actual_risk),
        "actual_risk_percent": float(actual_risk / balance * Decimal("100")),
        "gross_profit": float(profit),
        "gross_loss": float(actual_risk),
        "profile_status": "reference_estimate",
        "profile_disclosure": instrument["source_note"],
        "cost_disclosure": "Gross estimate before spread, commission, swap, slippage, gaps, and execution differences.",
        "price_precision": precision,
        "warnings": warnings,
        "learning": (
            f"At {symbol}, the reference model estimates a {stop_distance:.{precision}f} "
            f"price move to your stop as ${one_lot_loss:,.2f} per 1.00 lot. "
            f"Your planned risk of ${planned_risk:,.2f} implies {raw_volume:.4f} lots; "
            f"the displayed size is rounded to the permitted reference step. "
            f"The target is {rr:.2f} times the stop distance."
        ),
    }
