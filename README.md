# soft-yfinance-sample

A broad `yfinance` feature lab that stays GitHub Pages friendly.

## Verdict

`yfinance` itself is a Python library, so it does not run in the browser. That means a static host such as GitHub Pages cannot call `yfinance` at request time.

What does work well is this flow:

1. A Python script fetches market data with `yfinance`.
2. The script writes static JSON into `site/data/market-data.json`.
3. A plain HTML page reads that JSON and renders cards and small charts.
4. GitHub Actions regenerates the JSON on push or on a schedule, then deploys the static site to GitHub Pages.

That gives you a real `yfinance` example while keeping the deployed site fully static.

## What This Version Tests

The page now covers a much wider set of `yfinance` features:

- Cross-market quote snapshots for U.S., Korea, Japan, Europe, India, ETFs, crypto, FX, commodities, and indices
- `yf.Tickers(...)` batch containers
- `yf.download(...)` bulk history matrices
- `Search` and `Lookup`
- Predefined `screen(...)` queries
- `Market(...)` regional overviews
- `Sector(...)` and `Industry(...)`
- `Ticker.calendar`
- `Ticker.earnings_dates`
- `Ticker.recommendations`
- `Ticker.analyst_price_targets`
- `Ticker.income_stmt`, `Ticker.balance_sheet`, `Ticker.cashflow`
- `Ticker.major_holders`, `Ticker.institutional_holders`, `Ticker.mutualfund_holders`
- `Ticker.insider_transactions`, `Ticker.insider_purchases`, `Ticker.insider_roster_holders`
- `Ticker.upgrades_downgrades`
- `Ticker.sec_filings`
- `Ticker.news`
- `Ticker.options` and `option_chain(...)`
- `Ticker.funds_data` for ETF examples
- Library-level `WebSocket` and `AsyncWebSocket` availability checks

## Project Layout

```text
soft-yfinance-sample/
+-- .github/workflows/deploy-pages.yml
+-- requirements.txt
+-- scripts/generate_data.py
`-- site/
    +-- .nojekyll
    +-- app.js
    +-- index.html
    +-- styles.css
    `-- data/market-data.json
```

## Local Usage

### 1. Demo mode

This works without installing `yfinance` and lets you preview the static site immediately.

```bash
python scripts/generate_data.py --demo
python -m http.server 8000 -d site
```

Open `http://localhost:8000`.

### 2. Live market data

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts/generate_data.py
.venv\Scripts\python -m http.server 8000 -d site
```

Using a virtual environment is recommended because `yfinance`, `pandas`, and `numpy` can conflict with an older global Anaconda setup.

By default, the script fetches a built-in multi-market test set and generates:

- feature coverage status
- cross-market universes
- batch and bulk download tests
- search and lookup samples
- screener outputs
- market, sector, and industry overviews
- deep dives for `AAPL`, `005930.KS`, `SPY`, `BTC-USD`, and `EURUSD=X`

## Deploy To GitHub Pages

Create a public repo named `soft-yfinance-sample`, copy this folder into that repo root, then push it.

Example with GitHub CLI:

```bash
gh repo create soft-yfinance-sample --public --source . --push
```

The included workflow:

- installs Python and `yfinance`
- regenerates `site/data/market-data.json`
- deploys `site/` to GitHub Pages
- can also refresh on a daily schedule

After the first push:

1. Open the repository on GitHub.
2. Confirm Pages is using GitHub Actions as the deployment source.
3. Run the `Deploy GitHub Pages` workflow manually if you want the first deployment immediately.

## When To Use Vercel Instead

Use Vercel, a serverless function, or a small backend only if you want:

- request-time freshness
- user-entered ticker lookup
- secret-backed upstream calls
- caching or rate-limit control on the server

For a scheduled feature showcase or market snapshot lab, GitHub Pages is enough.
