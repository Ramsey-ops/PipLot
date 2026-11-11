from flask import Blueprint, jsonify, render_template, request

from app.instruments import get_instruments
from app.services.calculator import calculate_trade

main = Blueprint("main", __name__)


@main.get("/")
def home():
    return render_template("index.html")


@main.get("/api/instruments")
def instruments():
    return jsonify({"instruments": get_instruments()})


@main.post("/api/calculate")
def calculate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON request body is required."}), 400
    try:
        return jsonify(calculate_trade(data))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
