# India Intraday AI Scanner — Free Mobile Dashboard

A paper-trading/educational NSE scanner built with Python + Streamlit + Yahoo Finance data.

## What it does

- Scans a selectable NIFTY 50-style universe
- Uses 5-minute data
- Calculates EMA 9/20/50, RSI, ATR, session VWAP and volume ratio
- Detects 20-bar breakout/breakdown
- Produces a 0–100 setup score
- Shows BUY / WATCH / AVOID
- Calculates illustrative stop-loss and targets using ATR
- Calculates paper position size from account risk
- Displays a mobile-friendly Streamlit dashboard
- No broker login and no automatic order placement

## Important

This is NOT a guaranteed-return system. Free market-data feeds can be delayed, incomplete, rate-limited, or unavailable. Confirm prices, liquidity, spreads and corporate actions using your broker/NSE before placing any order.

## Run locally

Python 3.11 or 3.12 recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Then open the URL shown by Streamlit.

## Free cloud deployment

1. Create a GitHub repository.
2. Upload `app.py`, `requirements.txt`, and `README.md`.
3. Create/sign in to Streamlit Community Cloud.
4. Create an app and select your GitHub repository and `app.py`.
5. Deploy.
6. Open the resulting `streamlit.app` URL on your Android phone.
7. Use browser menu → Add to Home screen if desired.

No API key is required for this prototype.

## Suggested next upgrades

- Add NIFTY/SENSEX market-regime filter
- Add sector-relative strength
- Add opening-range breakout
- Add Supertrend
- Add trade journal and SQLite
- Add historical backtesting
- Add Telegram alerts
- Add broker API only after paper-testing
- Add walk-forward validation and transaction-cost/slippage modelling
