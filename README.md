# PipLot

PipLot is a browser-based, universal-style trade position calculator built with Flask, HTML, CSS, and vanilla JavaScript. It does not ask users to select a broker or enter technical contract specifications. It does not place orders.

## Important calculation limitation

The calculator distinguishes a reference estimate from an unavailable profile. USD-quoted forex pairs and USD-base forex pairs can be sized using the common 100,000-base-unit FX lot convention; USD-base pairs use the entered entry price as an estimated quote-to-USD conversion. XAUUSD can also be sized using a 100-unit contract size documented by FundedNext's Help Center for commodities. The FundedNext article says those contract sizes apply to all its accounts. For the generic PipLot calculator, minimum/step 0.01 and maximum 100 lots remain explicit assumptions, not facts from that source. None of these profiles are a broker quote or guarantee. Currency crosses that need a separate quote-to-USD conversion and CFDs without a defensible reference profile remain listed but unavailable for sizing.

FundedNext's Help Center states its lot-size calculator takes selected instrument, account balance, risk percentage, entry price, and exit price, and that calculator results are indicative. Its contract-size article documents forex at 100,000 and commodities at 100 except XAGUSD at 5,000; it does not provide the lot-step and limit assumptions used by PipLot. FundedNext is a public reference source here, not a claimed affiliation. All results exclude trading costs and execution differences.

Sources:

- [FundedNext Help Center: Does FundedNext offer any calculators?](https://help.fundednext.com/en/articles/11981961-does-fundednext-offer-any-calculators) (calculator inputs, availability, and indicative-results disclaimer)
- [FundedNext Help Center: What is the Contract Size of the instruments?](https://help.fundednext.com/en/articles/8020350-what-is-the-contract-size-of-the-instruments) (published product contract sizes)

The reference conventions and their disclosures are defined in `app/instruments.py`, separate from the calculation engine in `app/services/calculator.py`. Extend this data module only when a reliable reference basis is available; keep unavailable instruments visible rather than inventing specifications.

## Run locally

1. Install Python 3.10 or later.
2. From the project folder, create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

   For a deployed environment, set `FLASK_SECRET_KEY` to a long random value before startup. The local-only fallback is not for production.

4. Start the app:

   ```powershell
   python -m flask --app app:create_app run --debug
   ```

5. Open `http://127.0.0.1:5000`.

No MySQL database or account is required for this MVP. Favourites and recent plans are stored in the browser's local storage and can be cleared there or with the on-page control. No sensitive credentials or financial account data are collected.

## Deploy publicly for free

The included `render.yaml` configures a public Render web service on its free instance tier. Once deployed, Render provides an `https://<service-name>.onrender.com` address that works from phones, other computers, and browsers without your laptop running.

1. Put this project in a GitHub repository and push the files, including `render.yaml`.
2. Sign in to [Render](https://render.com), choose **New → Blueprint**, and connect the GitHub repository.
3. Review and apply the blueprint. Render installs the dependencies, generates `FLASK_SECRET_KEY`, and publishes the app at its public `onrender.com` URL.

The free web service may spin down after a period without requests, so the first visit after inactivity can take longer. The calculator does not need a database or any process running on your computer. Favourites and recent plans use each visitor's browser storage, so they are not shared or synchronized between devices.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use the explicitly labeled EURUSD and XAUUSD reference profiles and verify risk math, BUY/SELL and target handling, step rounding, validation, and the behavior for unavailable profiles.

## Project structure

```text
app/
  __init__.py
  routes.py
  instruments.py
  services/calculator.py
  templates/index.html
  static/css/style.css
  static/js/app.js
tests/
  test_calculator.py
requirements.txt
```
