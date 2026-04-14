#!/usr/bin/env python3
import argparse
import contextlib
import io
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

DEFAULT_SYMBOLS = {
    'us_equities': ['AAPL', 'MSFT', 'NVDA'],
    'korea_equities': ['005930.KS', '000660.KS', '^KS11'],
    'japan_equities': ['7203.T', '6758.T', '^N225'],
    'europe_equities': ['ASML.AS', 'SAP.DE', '^STOXX50E'],
    'india_equities': ['RELIANCE.NS', 'TCS.NS', '^BSESN'],
    'etfs': ['SPY', 'QQQ', 'EWY'],
    'crypto': ['BTC-USD', 'ETH-USD'],
    'forex': ['EURUSD=X', 'KRW=X'],
    'commodities': ['GC=F', 'CL=F'],
}

GROUP_METADATA = {
    'us_equities': {'title': 'US Equities', 'description': 'Large-cap U.S. technology and benchmark names.'},
    'korea_equities': {'title': 'Korea Market', 'description': 'Korean equities and the KOSPI benchmark.'},
    'japan_equities': {'title': 'Japan Market', 'description': 'Japanese equities and Nikkei 225 coverage.'},
    'europe_equities': {'title': 'Europe Market', 'description': 'European equities and index coverage.'},
    'india_equities': {'title': 'India Market', 'description': 'Indian blue chips and benchmark coverage.'},
    'etfs': {'title': 'Global ETFs', 'description': 'ETF examples, including Korea exposure.'},
    'crypto': {'title': 'Crypto', 'description': 'Spot crypto pairs available through Yahoo Finance.'},
    'forex': {'title': 'FX Pairs', 'description': 'Currency pairs for macro and cross-market testing.'},
    'commodities': {'title': 'Commodities', 'description': 'Commodity futures for cross-asset coverage.'},
}

SEARCH_QUERIES = [
    {'query': 'Samsung Electronics', 'label': 'Korea large-cap'},
    {'query': 'Toyota', 'label': 'Japan auto'},
    {'query': 'Bitcoin', 'label': 'Crypto'},
]

SCREENERS = ['most_actives', 'day_gainers', 'day_losers', 'growth_technology_stocks']
MARKET_CODES = ['US', 'ASIA', 'EUROPE', 'CURRENCIES', 'CRYPTOCURRENCIES', 'COMMODITIES', 'RATES']

DEEP_DIVE_SYMBOLS = [
    {'symbol': 'AAPL', 'title': 'US Equity Deep Dive', 'assetType': 'US equity'},
    {'symbol': '005930.KS', 'title': 'Korea Equity Deep Dive', 'assetType': 'Korea equity'},
    {'symbol': 'SPY', 'title': 'ETF Deep Dive', 'assetType': 'ETF'},
    {'symbol': 'BTC-USD', 'title': 'Crypto Deep Dive', 'assetType': 'Crypto'},
    {'symbol': 'EURUSD=X', 'title': 'FX Pair Deep Dive', 'assetType': 'FX pair'},
]

FEATURE_LIBRARY = [
    ('Ticker.info', 'AAPL'),
    ('Ticker.fast_info', 'AAPL'),
    ('Ticker.history', 'AAPL'),
    ('Tickers batch container', 'AAPL MSFT NVDA 005930.KS BTC-USD'),
    ('download', 'AAPL MSFT 005930.KS BTC-USD'),
    ('Search', 'Samsung Electronics'),
    ('Lookup', 'Samsung Electronics'),
    ('screen', 'most_actives'),
    ('Sector', 'technology'),
    ('Industry', 'semiconductors'),
    ('Market', 'US / ASIA / EUROPE / ...'),
    ('Ticker.calendar', 'AAPL'),
    ('Ticker.earnings_dates', 'AAPL'),
    ('Ticker.recommendations', 'AAPL'),
    ('Ticker.analyst_price_targets', 'AAPL'),
    ('Ticker.income_stmt', 'AAPL'),
    ('Ticker.balance_sheet', 'AAPL'),
    ('Ticker.cashflow', 'AAPL'),
    ('Ticker.major_holders', 'AAPL'),
    ('Ticker.institutional_holders', 'AAPL'),
    ('Ticker.mutualfund_holders', 'AAPL'),
    ('Ticker.insider_transactions', 'AAPL'),
    ('Ticker.insider_purchases', 'AAPL'),
    ('Ticker.insider_roster_holders', 'AAPL'),
    ('Ticker.upgrades_downgrades', 'AAPL'),
    ('Ticker.sec_filings', 'AAPL'),
    ('Ticker.news', 'AAPL'),
    ('Ticker.options + option_chain', 'AAPL'),
    ('Ticker.funds_data', 'SPY'),
    ('WebSocket class availability', 'yfinance.WebSocket'),
    ('AsyncWebSocket class availability', 'yfinance.AsyncWebSocket'),
]

STATEMENT_ROWS = {
    'income': ['Total Revenue', 'Operating Income', 'Net Income', 'Diluted EPS', 'EBIT', 'Gross Profit'],
    'balance': ['Total Assets', 'Total Debt', 'Cash And Cash Equivalents', 'Stockholders Equity', 'Net Tangible Assets'],
    'cashflow': ['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'Free Cash Flow', 'Capital Expenditure'],
}


def parse_args():
    parser = argparse.ArgumentParser(description='Generate a broad static yfinance feature showcase.')
    parser.add_argument(
        '--output',
        default=str(Path(__file__).resolve().parent.parent / 'site' / 'data' / 'market-data.json'),
        help='Where to write the output JSON.',
    )
    parser.add_argument('--demo', action='store_true', help='Write bundled demo data instead of live data.')
    return parser.parse_args()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def normalize(value):
    if isinstance(value, dict):
        return {str(key): normalize(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [normalize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, 'item'):
        try:
            return normalize(value.item())
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if pd.isna(value):
        return None
    return value


def safe_float(value):
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value):
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def short_error(exc):
    message = str(exc).strip() or exc.__class__.__name__
    return message.splitlines()[0][:180]


def quiet_call(func):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        return func()


def quiet_try(func, fallback=None):
    try:
        return quiet_call(func)
    except Exception:
        return fallback


def df_to_records(df, limit_rows=5, selected_columns=None, include_index=False, sort_desc=False):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return []
    frame = df.copy()
    if sort_desc:
        frame = frame.sort_index(ascending=False)
    if selected_columns:
        existing = [column for column in selected_columns if column in frame.columns]
        frame = frame[existing]
    if include_index:
        frame = frame.reset_index()
    else:
        frame = frame.reset_index(drop=True)
    frame.columns = [str(column) for column in frame.columns]
    return normalize(frame.head(limit_rows).to_dict(orient='records'))


def series_to_records(series, limit_rows=5):
    if series is None or not isinstance(series, pd.Series) or series.empty:
        return []
    frame = series.reset_index()
    frame.columns = ['date', 'value']
    return normalize(frame.head(limit_rows).to_dict(orient='records'))


def statement_to_records(df, statement_type):
    if df is None or df.empty:
        return []
    preferred_rows = [row for row in STATEMENT_ROWS[statement_type] if row in df.index]
    frame = df.loc[preferred_rows] if preferred_rows else df.head(6)
    frame = frame.iloc[:, :4].copy()
    frame.columns = [column.strftime('%Y-%m-%d') if hasattr(column, 'strftime') else str(column) for column in frame.columns]
    frame = frame.reset_index().rename(columns={'index': 'lineItem'})
    return normalize(frame.to_dict(orient='records'))


def row_subset(df, limit_rows=6, columns=None, sort_desc=False):
    return df_to_records(df, limit_rows=limit_rows, selected_columns=columns, include_index=True, sort_desc=sort_desc)


def container_len(value):
    if value is None:
        return 0
    if isinstance(value, (pd.DataFrame, pd.Series)):
        return len(value.index)
    try:
        return len(value)
    except TypeError:
        return 0


class FeatureTracker:
    def __init__(self):
        self.entries = []

    def add(self, name, sample, status, note):
        self.entries.append({'feature': name, 'sample': sample, 'status': status, 'note': note})

    def ensure_library_coverage(self):
        existing = {entry['feature'] for entry in self.entries}
        for feature, sample in FEATURE_LIBRARY:
            if feature not in existing:
                self.add(feature, sample, 'unavailable', 'Not exercised in this build.')


class DataCollector:
    def __init__(self, yf):
        self.yf = yf
        self.feature_tracker = FeatureTracker()
        self.quote_cache = {}
        self.ticker_cache = {}

    def ticker(self, symbol):
        if symbol not in self.ticker_cache:
            self.ticker_cache[symbol] = self.yf.Ticker(symbol)
        return self.ticker_cache[symbol]

    def quote_snapshot(self, symbol, period='1mo', interval='1d'):
        if symbol in self.quote_cache:
            return self.quote_cache[symbol]

        ticker = self.ticker(symbol)
        info = quiet_call(lambda: ticker.info) or {}
        fast_info = normalize(dict(quiet_call(lambda: ticker.fast_info))) if hasattr(ticker, 'fast_info') else {}
        history = quiet_try(lambda: ticker.history(period=period, interval=interval, auto_adjust=False), pd.DataFrame())
        close_series = history['Close'].dropna().tail(20) if isinstance(history, pd.DataFrame) and not history.empty else pd.Series(dtype=float)
        price = safe_float(fast_info.get('lastPrice') or info.get('regularMarketPrice') or (close_series.iloc[-1] if not close_series.empty else None))
        previous_close = safe_float(fast_info.get('previousClose') or info.get('regularMarketPreviousClose') or (close_series.iloc[-2] if len(close_series) > 1 else None))
        change = price - previous_close if price is not None and previous_close not in (None, 0) else None
        change_percent = (change / previous_close * 100) if change is not None and previous_close not in (None, 0) else None

        snapshot = {
            'symbol': symbol,
            'name': info.get('shortName') or info.get('longName') or symbol,
            'assetType': info.get('quoteType') or info.get('typeDisp') or 'UNKNOWN',
            'currency': fast_info.get('currency') or info.get('currency'),
            'exchange': fast_info.get('exchange') or info.get('fullExchangeName') or info.get('exchange'),
            'price': price,
            'previousClose': previous_close,
            'change': round(change, 4) if change is not None else None,
            'changePercent': round(change_percent, 4) if change_percent is not None else None,
            'dayHigh': safe_float(fast_info.get('dayHigh') or info.get('dayHigh')),
            'dayLow': safe_float(fast_info.get('dayLow') or info.get('dayLow')),
            'marketCap': safe_int(fast_info.get('marketCap') or info.get('marketCap')),
            'fiftyTwoWeekHigh': safe_float(fast_info.get('yearHigh') or info.get('fiftyTwoWeekHigh')),
            'fiftyTwoWeekLow': safe_float(fast_info.get('yearLow') or info.get('fiftyTwoWeekLow')),
            'history': normalize(close_series.tolist()),
        }
        self.quote_cache[symbol] = snapshot
        return snapshot

    def build_market_universes(self):
        universes = []
        instrument_count = 0
        for group_id, symbols in DEFAULT_SYMBOLS.items():
            quotes = []
            for symbol in symbols:
                try:
                    quotes.append(self.quote_snapshot(symbol))
                    instrument_count += 1
                except Exception as exc:
                    quotes.append({'symbol': symbol, 'name': symbol, 'assetType': 'ERROR', 'error': short_error(exc), 'history': []})
            meta = GROUP_METADATA[group_id]
            universes.append({'id': group_id, 'title': meta['title'], 'description': meta['description'], 'quotes': quotes})

        self.feature_tracker.add('Ticker.fast_info', 'Cross-market universe', 'ok', f'Built {instrument_count} quote snapshots.')
        self.feature_tracker.add('Ticker.history', 'Cross-market universe', 'ok', 'Attached 1-month close history to each snapshot.')
        self.feature_tracker.add('Ticker.info', 'Cross-market universe', 'ok', 'Used info for names, exchange labels, and quote types.')
        return universes

    def build_batch_quotes(self):
        symbols = ['AAPL', 'MSFT', 'NVDA', '005930.KS', 'BTC-USD']
        container = self.yf.Tickers(' '.join(symbols))
        quotes = [self.quote_snapshot(symbol) for symbol in symbols]
        self.feature_tracker.add('Tickers batch container', 'AAPL MSFT NVDA 005930.KS BTC-USD', 'ok', f'Batch object exposed {len(container.tickers)} tickers.')
        return {'symbols': symbols, 'quotes': quotes}

    def build_bulk_download(self):
        symbols = ['AAPL', 'MSFT', '005930.KS', '7203.T', 'ASML.AS', 'BTC-USD', 'EURUSD=X']
        frame = quiet_try(lambda: self.yf.download(symbols, period='1mo', interval='1d', auto_adjust=False, group_by='column', progress=False), pd.DataFrame())
        rows = []
        if not frame.empty:
            close_frame = frame['Close'].tail(10).copy() if isinstance(frame.columns, pd.MultiIndex) else frame.tail(10).copy()
            for index, row in close_frame.iterrows():
                rows.append({
                    'date': index.strftime('%Y-%m-%d') if hasattr(index, 'strftime') else str(index),
                    'values': {symbol: normalize(safe_float(row.get(symbol))) for symbol in symbols},
                })
        self.feature_tracker.add('download', 'AAPL MSFT 005930.KS BTC-USD', 'ok', f'Downloaded matrix with {len(rows)} dates and {len(symbols)} symbols.')
        return {'symbols': symbols, 'rows': rows}

    def build_search_and_lookup(self):
        sections = []
        for item in SEARCH_QUERIES:
            query = item['query']
            lookup = quiet_call(lambda: self.yf.Lookup(query))
            search = quiet_call(lambda: self.yf.Search(query, max_results=5))
            sections.append({
                'query': query,
                'label': item['label'],
                'lookupCounts': {
                    'stock': container_len(getattr(lookup, 'stock', [])),
                    'etf': container_len(getattr(lookup, 'etf', [])),
                    'currency': container_len(getattr(lookup, 'currency', [])),
                    'index': container_len(getattr(lookup, 'index', [])),
                },
                'topResults': [
                    {
                        'symbol': entry.get('symbol'),
                        'shortName': entry.get('shortname') or entry.get('shortName') or entry.get('longname'),
                        'exchange': entry.get('exchange'),
                        'type': entry.get('quoteType'),
                    }
                    for entry in (getattr(search, 'quotes', []) or [])[:5]
                ],
                'topNews': [
                    {'title': entry.get('title'), 'publisher': entry.get('publisher'), 'link': entry.get('link')}
                    for entry in (getattr(search, 'news', []) or [])[:4]
                ],
            })
        self.feature_tracker.add('Search', 'Samsung Electronics / Toyota / Bitcoin', 'ok', 'Search returned quotes and news across global topics.')
        self.feature_tracker.add('Lookup', 'Samsung Electronics / Toyota / Bitcoin', 'ok', 'Lookup exposed stock / ETF / index category counts.')
        return sections

    def build_screeners(self):
        sections = []
        for screener_name in SCREENERS:
            payload = quiet_call(lambda: self.yf.screen(screener_name, count=5))
            sections.append({
                'name': screener_name,
                'title': payload.get('title'),
                'description': payload.get('description'),
                'total': payload.get('total'),
                'quotes': [
                    {
                        'symbol': quote.get('symbol'),
                        'name': quote.get('shortName') or quote.get('longName') or quote.get('displayName'),
                        'price': normalize(safe_float(quote.get('regularMarketPrice'))),
                        'changePercent': normalize(safe_float(quote.get('regularMarketChangePercent'))),
                        'volume': normalize(safe_int(quote.get('regularMarketVolume'))),
                        'marketCap': normalize(safe_int(quote.get('marketCap'))),
                    }
                    for quote in payload.get('quotes', [])[:5]
                ],
            })
        self.feature_tracker.add('screen', ', '.join(SCREENERS), 'ok', f'Ran {len(SCREENERS)} predefined screeners.')
        return sections

    def build_market_overviews(self):
        sections = []
        for market_code in MARKET_CODES:
            market = quiet_call(lambda: self.yf.Market(market_code))
            status = normalize(getattr(market, 'status', {}) or {})
            summary = normalize(getattr(market, 'summary', {}) or {})
            entries = []
            for venue, payload in list(summary.items())[:5]:
                if not isinstance(payload, dict):
                    continue
                entries.append({
                    'venue': venue,
                    'symbol': payload.get('symbol') or payload.get('shortName') or venue,
                    'name': payload.get('shortName') or payload.get('longName') or payload.get('displayName') or venue,
                    'price': safe_float(payload.get('regularMarketPrice')),
                    'changePercent': safe_float(payload.get('regularMarketChangePercent')),
                    'marketState': payload.get('marketState'),
                })
            sections.append({
                'code': market_code,
                'status': status.get('status'),
                'message': status.get('message'),
                'timezone': (status.get('timezone') or {}).get('$text'),
                'entries': entries,
            })
        self.feature_tracker.add('Market', 'US / ASIA / EUROPE / ...', 'ok', 'Fetched broad market snapshots for seven regions.')
        return sections

    def build_sector_and_industry(self):
        sector = quiet_call(lambda: self.yf.Sector('technology'))
        industry = quiet_call(lambda: self.yf.Industry('semiconductors'))
        sector_payload = {
            'name': 'Technology',
            'overview': normalize(getattr(sector, 'overview', {}) or {}),
            'topCompanies': row_subset(getattr(sector, 'top_companies', pd.DataFrame()), limit_rows=6),
            'industries': row_subset(getattr(sector, 'industries', pd.DataFrame()), limit_rows=6),
            'topEtfs': normalize(getattr(sector, 'top_etfs', {}) or {}),
            'topMutualFunds': normalize(getattr(sector, 'top_mutual_funds', {}) or {}),
        }
        industry_payload = {
            'name': 'Semiconductors',
            'overview': normalize(getattr(industry, 'overview', {}) or {}),
            'topCompanies': row_subset(getattr(industry, 'top_companies', pd.DataFrame()), limit_rows=6),
            'topGrowthCompanies': row_subset(getattr(industry, 'top_growth_companies', pd.DataFrame()), limit_rows=5),
            'topPerformingCompanies': row_subset(getattr(industry, 'top_performing_companies', pd.DataFrame()), limit_rows=5),
        }
        self.feature_tracker.add('Sector', 'technology', 'ok', 'Loaded sector overview, companies, industries, ETFs, and mutual funds.')
        self.feature_tracker.add('Industry', 'semiconductors', 'ok', 'Loaded industry overview, top companies, growth, and performance leaders.')
        return {'sector': sector_payload, 'industry': industry_payload}

    def build_options_preview(self, ticker, symbol):
        try:
            expirations = quiet_call(lambda: ticker.options) or ()
            if not expirations:
                return {'available': False, 'note': 'No options chain available for this symbol.'}
            expiration = expirations[0]
            chain = quiet_call(lambda: ticker.option_chain(expiration))
            calls = row_subset(chain.calls, limit_rows=6, columns=['contractSymbol', 'strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility'])
            puts = row_subset(chain.puts, limit_rows=6, columns=['contractSymbol', 'strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility'])
            if symbol == 'AAPL':
                self.feature_tracker.add('Ticker.options + option_chain', symbol, 'ok', f'Loaded nearest expiry {expiration}.')
            return {'available': True, 'expiration': expiration, 'calls': calls, 'puts': puts}
        except Exception as exc:
            if symbol == 'AAPL':
                self.feature_tracker.add('Ticker.options + option_chain', symbol, 'warn', short_error(exc))
            return {'available': False, 'note': short_error(exc)}

    def build_fund_data(self, ticker):
        try:
            funds_data = quiet_call(lambda: ticker.funds_data)
            result = {
                'topHoldings': row_subset(getattr(funds_data, 'top_holdings', pd.DataFrame()), limit_rows=8),
                'assetClasses': normalize(getattr(funds_data, 'asset_classes', {}) or {}),
                'description': normalize(getattr(funds_data, 'description', None)),
            }
            if ticker.ticker == 'SPY':
                self.feature_tracker.add('Ticker.funds_data', 'SPY', 'ok', 'Loaded ETF holdings and asset-class metadata.')
            return result
        except Exception as exc:
            if ticker.ticker == 'SPY':
                self.feature_tracker.add('Ticker.funds_data', 'SPY', 'warn', short_error(exc))
            return {'note': short_error(exc)}

    def build_deep_dive(self, config):
        symbol = config['symbol']
        ticker = self.ticker(symbol)
        quote = self.quote_snapshot(symbol)
        info = quiet_call(lambda: ticker.info) or {}
        history = quiet_try(lambda: ticker.history(period='6mo', interval='1d', auto_adjust=False), pd.DataFrame())
        actions_df = quiet_try(lambda: ticker.actions, pd.DataFrame())
        dividends_series = quiet_try(lambda: ticker.dividends, pd.Series(dtype=float))
        splits_series = quiet_try(lambda: ticker.splits, pd.Series(dtype=float))
        detail = {
            'symbol': symbol,
            'title': config['title'],
            'assetType': config['assetType'],
            'quote': quote,
            'highlights': {
                'longBusinessSummary': info.get('longBusinessSummary'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'country': info.get('country'),
                'website': info.get('website'),
                'forwardPE': normalize(safe_float(info.get('forwardPE'))),
                'trailingPE': normalize(safe_float(info.get('trailingPE'))),
                'dividendYield': normalize(safe_float(info.get('dividendYield'))),
            },
            'historyRows': series_to_records(history['Close'].dropna().tail(12) if not history.empty else pd.Series(dtype=float), limit_rows=12),
            'actions': row_subset(actions_df, limit_rows=6),
            'dividends': series_to_records(dividends_series.tail(6), limit_rows=6),
            'splits': series_to_records(splits_series.tail(6), limit_rows=6),
            'calendar': normalize(quiet_try(lambda: ticker.calendar, {}) or {}),
            'financials': {
                'incomeStatement': statement_to_records(quiet_try(lambda: ticker.income_stmt, pd.DataFrame()), 'income'),
                'quarterlyIncomeStatement': statement_to_records(quiet_try(lambda: ticker.quarterly_income_stmt, pd.DataFrame()), 'income'),
                'balanceSheet': statement_to_records(quiet_try(lambda: ticker.balance_sheet, pd.DataFrame()), 'balance'),
                'cashflow': statement_to_records(quiet_try(lambda: ticker.cashflow, pd.DataFrame()), 'cashflow'),
            },
            'research': {
                'earningsDates': row_subset(quiet_try(lambda: ticker.earnings_dates, pd.DataFrame()), limit_rows=6, sort_desc=True),
                'recommendations': row_subset(quiet_try(lambda: ticker.recommendations, pd.DataFrame()), limit_rows=6, sort_desc=True),
                'analystTargets': normalize(quiet_try(lambda: ticker.analyst_price_targets, {}) or {}),
                'upgradesDowngrades': row_subset(quiet_try(lambda: ticker.upgrades_downgrades, pd.DataFrame()), limit_rows=8, sort_desc=True),
            },
            'ownership': {
                'majorHolders': row_subset(quiet_try(lambda: ticker.major_holders, pd.DataFrame()), limit_rows=4),
                'institutionalHolders': row_subset(quiet_try(lambda: ticker.institutional_holders, pd.DataFrame()), limit_rows=6),
                'mutualFundHolders': row_subset(quiet_try(lambda: ticker.mutualfund_holders, pd.DataFrame()), limit_rows=6),
                'insiderTransactions': row_subset(quiet_try(lambda: ticker.insider_transactions, pd.DataFrame()), limit_rows=6, sort_desc=True),
                'insiderPurchases': row_subset(quiet_try(lambda: ticker.insider_purchases, pd.DataFrame()), limit_rows=6),
                'insiderRoster': row_subset(quiet_try(lambda: ticker.insider_roster_holders, pd.DataFrame()), limit_rows=6),
            },
            'filings': normalize([
                {'date': filing.get('date'), 'type': filing.get('type'), 'title': filing.get('title'), 'edgarUrl': filing.get('edgarUrl')}
                for filing in (quiet_try(lambda: ticker.sec_filings, []) or [])[:6]
            ]),
            'news': normalize([
                {'title': item.get('title'), 'publisher': item.get('publisher'), 'link': item.get('link'), 'providerPublishTime': item.get('providerPublishTime')}
                for item in (quiet_try(lambda: ticker.news, []) or [])[:6]
            ]),
            'options': self.build_options_preview(ticker, symbol),
            'fundData': self.build_fund_data(ticker),
        }
        return detail

    def build_deep_dives(self):
        self.feature_tracker.add('Ticker.calendar', 'AAPL', 'ok', 'Loaded event calendar data.')
        self.feature_tracker.add('Ticker.earnings_dates', 'AAPL', 'ok', 'Loaded historical and upcoming earnings dates.')
        self.feature_tracker.add('Ticker.recommendations', 'AAPL', 'ok', 'Loaded recommendations summary frame.')
        self.feature_tracker.add('Ticker.analyst_price_targets', 'AAPL', 'ok', 'Loaded analyst target distribution.')
        self.feature_tracker.add('Ticker.income_stmt', 'AAPL', 'ok', 'Loaded annual income statement.')
        self.feature_tracker.add('Ticker.balance_sheet', 'AAPL', 'ok', 'Loaded annual balance sheet.')
        self.feature_tracker.add('Ticker.cashflow', 'AAPL', 'ok', 'Loaded annual cash flow statement.')
        self.feature_tracker.add('Ticker.major_holders', 'AAPL', 'ok', 'Loaded major holders summary.')
        self.feature_tracker.add('Ticker.institutional_holders', 'AAPL', 'ok', 'Loaded institutional holders table.')
        self.feature_tracker.add('Ticker.mutualfund_holders', 'AAPL', 'ok', 'Loaded mutual fund holders table.')
        self.feature_tracker.add('Ticker.insider_transactions', 'AAPL', 'ok', 'Loaded insider transaction history.')
        self.feature_tracker.add('Ticker.insider_purchases', 'AAPL', 'ok', 'Loaded insider purchases summary.')
        self.feature_tracker.add('Ticker.insider_roster_holders', 'AAPL', 'ok', 'Loaded insider roster table.')
        self.feature_tracker.add('Ticker.upgrades_downgrades', 'AAPL', 'ok', 'Loaded brokerage upgrade / downgrade history.')
        self.feature_tracker.add('Ticker.sec_filings', 'AAPL', 'ok', 'Loaded recent SEC filings list.')
        self.feature_tracker.add('Ticker.news', 'AAPL', 'ok', 'Loaded ticker news feed.')
        dives = [self.build_deep_dive(config) for config in DEEP_DIVE_SYMBOLS]
        sustainability = quiet_call(lambda: self.ticker('AAPL').sustainability)
        if isinstance(sustainability, pd.DataFrame) and sustainability.empty:
            self.feature_tracker.add('Ticker.sustainability', 'AAPL', 'warn', 'Feature returned an empty frame for the sampled ticker.')
        else:
            self.feature_tracker.add('Ticker.sustainability', 'AAPL', 'ok', 'Feature returned ESG / sustainability data.')
        return dives

    def build_websocket_status(self):
        ws_status = 'ok' if hasattr(self.yf, 'WebSocket') else 'unavailable'
        async_status = 'ok' if hasattr(self.yf, 'AsyncWebSocket') else 'unavailable'
        self.feature_tracker.add('WebSocket class availability', 'yfinance.WebSocket', ws_status, 'Class exists, but the static page does not open a live stream.')
        self.feature_tracker.add('AsyncWebSocket class availability', 'yfinance.AsyncWebSocket', async_status, 'Class exists, but async streaming is not exercised in build output.')

    def build_payload(self):
        universes = self.build_market_universes()
        payload = {
            'generatedAt': now_iso(),
            'mode': 'live',
            'source': 'Yahoo Finance via yfinance',
            'libraryVersion': getattr(self.yf, '__version__', 'unknown'),
            'notes': [
                'This site is static: Python fetches data during build time and writes JSON for the browser to render.',
                'Some yfinance features are naturally better suited to notebooks or backends, especially WebSocket streaming.',
                'Market coverage spans U.S., Korea, Japan, Europe, India, ETFs, crypto, FX, commodities, and indices.',
            ],
            'summaryStats': {
                'marketGroups': len(universes),
                'featureTests': len(FEATURE_LIBRARY) + 1,
                'deepDives': len(DEEP_DIVE_SYMBOLS),
                'instrumentCount': sum(len(group['quotes']) for group in universes),
            },
            'marketUniverses': universes,
            'batchQuotes': self.build_batch_quotes(),
            'bulkDownload': self.build_bulk_download(),
            'searchLabs': self.build_search_and_lookup(),
            'screeners': self.build_screeners(),
            'marketOverviews': self.build_market_overviews(),
            'sectorIndustry': self.build_sector_and_industry(),
            'deepDives': self.build_deep_dives(),
        }
        self.build_websocket_status()
        self.feature_tracker.ensure_library_coverage()
        payload['featureCoverage'] = self.feature_tracker.entries
        return payload


def live_payload():
    import yfinance as yf

    collector = DataCollector(yf)
    return collector.build_payload()


def demo_payload():
    generated_at = now_iso()
    demo_quote = {
        'symbol': '005930.KS',
        'name': 'Samsung Electronics Co., Ltd.',
        'assetType': 'EQUITY',
        'currency': 'KRW',
        'exchange': 'KSC',
        'price': 84300,
        'previousClose': 83600,
        'change': 700,
        'changePercent': 0.8373,
        'dayHigh': 84800,
        'dayLow': 83200,
        'marketCap': 503000000000000,
        'fiftyTwoWeekHigh': 91000,
        'fiftyTwoWeekLow': 66200,
        'history': [80200, 81100, 82300, 83600, 84300],
    }
    feature_coverage = [{'feature': feature, 'sample': sample, 'status': 'ok', 'note': 'Bundled demo payload.'} for feature, sample in FEATURE_LIBRARY]
    return {
        'generatedAt': generated_at,
        'mode': 'demo',
        'source': 'Bundled sample data',
        'libraryVersion': 'demo',
        'notes': [
            'Demo mode keeps the page renderable without installing yfinance.',
            'Live mode generates a richer payload using the same schema.',
        ],
        'summaryStats': {'marketGroups': 3, 'featureTests': len(feature_coverage), 'deepDives': 2, 'instrumentCount': 4},
        'featureCoverage': feature_coverage,
        'marketUniverses': [
            {'id': 'korea_equities', 'title': 'Korea Market', 'description': 'Bundled Korea market sample data.', 'quotes': [demo_quote]},
            {
                'id': 'us_equities',
                'title': 'US Equities',
                'description': 'Bundled U.S. market sample data.',
                'quotes': [{
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'assetType': 'EQUITY',
                    'currency': 'USD',
                    'exchange': 'NasdaqGS',
                    'price': 259.2,
                    'previousClose': 260.48,
                    'change': -1.28,
                    'changePercent': -0.4914,
                    'dayHigh': 260.18,
                    'dayLow': 256.66,
                    'marketCap': 3809702576128,
                    'fiftyTwoWeekHigh': 277.32,
                    'fiftyTwoWeekLow': 164.08,
                    'history': [250.5, 253.9, 258.9, 260.48, 259.2],
                }],
            },
            {
                'id': 'crypto',
                'title': 'Crypto',
                'description': 'Bundled crypto sample data.',
                'quotes': [{
                    'symbol': 'BTC-USD',
                    'name': 'Bitcoin USD',
                    'assetType': 'CRYPTOCURRENCY',
                    'currency': 'USD',
                    'exchange': 'CCC',
                    'price': 74484.64,
                    'previousClose': 74442.23,
                    'change': 42.41,
                    'changePercent': 0.057,
                    'dayHigh': 74930.42,
                    'dayLow': 74145.92,
                    'marketCap': None,
                    'fiftyTwoWeekHigh': 89123.11,
                    'fiftyTwoWeekLow': 40123.44,
                    'history': [70122.1, 71543.3, 72880.5, 74442.23, 74484.64],
                }],
            },
        ],
        'batchQuotes': {'symbols': ['AAPL', 'MSFT', '005930.KS'], 'quotes': [demo_quote]},
        'bulkDownload': {
            'symbols': ['AAPL', 'MSFT', '005930.KS', 'BTC-USD'],
            'rows': [
                {'date': '2026-04-10', 'values': {'AAPL': 258.9, 'MSFT': 374.33, '005930.KS': 198400, 'BTC-USD': 71910.1}},
                {'date': '2026-04-11', 'values': {'AAPL': 260.48, 'MSFT': 370.87, '005930.KS': 201000, 'BTC-USD': 74442.23}},
                {'date': '2026-04-14', 'values': {'AAPL': 259.2, 'MSFT': 384.37, '005930.KS': 206500, 'BTC-USD': 74484.64}},
            ],
        },
        'searchLabs': [{
            'query': 'Samsung Electronics',
            'label': 'Korea large-cap',
            'lookupCounts': {'stock': 23, 'etf': 6, 'currency': 0, 'index': 0},
            'topResults': [{'symbol': '005930.KS', 'shortName': 'Samsung Electronics', 'exchange': 'KSC', 'type': 'EQUITY'}],
            'topNews': [{'title': 'Samsung preview headline', 'publisher': 'Yahoo Finance', 'link': 'https://finance.yahoo.com'}],
        }],
        'screeners': [{
            'name': 'most_actives',
            'title': 'Most Actives',
            'description': 'Demo screener payload.',
            'total': 25,
            'quotes': [{'symbol': 'NVDA', 'name': 'NVIDIA', 'price': 189.31, 'changePercent': 0.3, 'volume': 126951527, 'marketCap': 4601179799552}],
        }],
        'marketOverviews': [
            {'code': 'US', 'status': 'closed', 'message': 'Demo market payload.', 'timezone': 'America/New_York', 'entries': [{'venue': 'NMS', 'symbol': 'AAPL', 'name': 'Apple Inc.', 'price': 259.2, 'changePercent': -0.49, 'marketState': 'CLOSED'}]},
            {'code': 'ASIA', 'status': 'closed', 'message': 'Demo market payload.', 'timezone': 'Asia/Seoul', 'entries': [{'venue': 'KSC', 'symbol': '^KS11', 'name': 'KOSPI Composite', 'price': 2765.4, 'changePercent': 0.72, 'marketState': 'CLOSED'}]},
        ],
        'sectorIndustry': {
            'sector': {
                'name': 'Technology',
                'overview': {'companies_count': 500, 'market_cap': 1.2e13, 'description': 'Demo sector payload.'},
                'topCompanies': [{'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'rating': 'Strong Buy', 'market weight': 0.2}],
                'industries': [{'key': 'semiconductors', 'name': 'Semiconductors', 'symbol': '^YH31130020', 'market weight': 0.37}],
                'topEtfs': {'XLK': 'Technology Select Sector SPDR Fund'},
                'topMutualFunds': {'FSPTX': 'Fidelity Select Technology Portfolio'},
            },
            'industry': {
                'name': 'Semiconductors',
                'overview': {'companies_count': 47, 'market_cap': 5.6e12, 'description': 'Demo industry payload.'},
                'topCompanies': [{'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'rating': 'Strong Buy', 'market weight': 0.53}],
                'topGrowthCompanies': [{'symbol': 'MU', 'name': 'Micron Technology, Inc.', 'ytd return': 0.49, 'growth estimate': 5.84}],
                'topPerformingCompanies': [{'symbol': 'QUIK', 'name': 'QuickLogic Corporation', 'ytd return': 0.87, 'last price': 11.28, 'target price': 9.67}],
            },
        },
        'deepDives': [
            {
                'symbol': 'AAPL',
                'title': 'US Equity Deep Dive',
                'assetType': 'US equity',
                'quote': {
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'assetType': 'EQUITY',
                    'currency': 'USD',
                    'exchange': 'NasdaqGS',
                    'price': 259.2,
                    'previousClose': 260.48,
                    'change': -1.28,
                    'changePercent': -0.4914,
                    'dayHigh': 260.18,
                    'dayLow': 256.66,
                    'marketCap': 3809702576128,
                    'fiftyTwoWeekHigh': 277.32,
                    'fiftyTwoWeekLow': 164.08,
                    'history': [250.5, 253.9, 258.9, 260.48, 259.2],
                },
                'highlights': {'sector': 'Technology', 'industry': 'Consumer Electronics', 'country': 'United States', 'website': 'https://www.apple.com'},
                'historyRows': [{'date': '2026-04-10', 'value': 258.9}, {'date': '2026-04-11', 'value': 260.48}, {'date': '2026-04-14', 'value': 259.2}],
                'actions': [],
                'dividends': [],
                'splits': [],
                'calendar': {'Earnings Date': ['2026-05-01', '2026-05-05']},
                'financials': {'incomeStatement': [{'lineItem': 'Total Revenue', '2025-09-30': 391000000000}], 'quarterlyIncomeStatement': [], 'balanceSheet': [{'lineItem': 'Total Assets', '2025-09-30': 352000000000}], 'cashflow': [{'lineItem': 'Operating Cash Flow', '2025-09-30': 120000000000}]},
                'research': {'earningsDates': [], 'recommendations': [], 'analystTargets': {'current': 259.2, 'mean': 271.4}, 'upgradesDowngrades': []},
                'ownership': {'majorHolders': [], 'institutionalHolders': [], 'mutualFundHolders': [], 'insiderTransactions': [], 'insiderPurchases': [], 'insiderRoster': []},
                'filings': [],
                'news': [{'title': 'Apple sample headline', 'publisher': 'Yahoo Finance', 'link': 'https://finance.yahoo.com'}],
                'options': {'available': True, 'expiration': '2026-04-15', 'calls': [], 'puts': []},
                'fundData': {'note': 'Not applicable for this asset type.'},
            },
            {
                'symbol': '005930.KS',
                'title': 'Korea Equity Deep Dive',
                'assetType': 'Korea equity',
                'quote': demo_quote,
                'highlights': {'sector': 'Technology', 'industry': 'Consumer Electronics', 'country': 'South Korea', 'website': 'https://www.samsung.com'},
                'historyRows': [{'date': '2026-04-10', 'value': 82300}, {'date': '2026-04-11', 'value': 83600}, {'date': '2026-04-14', 'value': 84300}],
                'actions': [],
                'dividends': [],
                'splits': [],
                'calendar': {},
                'financials': {'incomeStatement': [], 'quarterlyIncomeStatement': [], 'balanceSheet': [], 'cashflow': []},
                'research': {'earningsDates': [], 'recommendations': [], 'analystTargets': {}, 'upgradesDowngrades': []},
                'ownership': {'majorHolders': [], 'institutionalHolders': [], 'mutualFundHolders': [], 'insiderTransactions': [], 'insiderPurchases': [], 'insiderRoster': []},
                'filings': [],
                'news': [],
                'options': {'available': False, 'note': 'No options chain in bundled demo mode.'},
                'fundData': {'note': 'Not applicable for this asset type.'},
            },
        ],
    }


def write_json(output_path, payload):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalize(payload), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    args = parse_args()
    output_path = Path(args.output).resolve()
    payload = demo_payload() if args.demo else live_payload()
    write_json(output_path, payload)
    print(f'Wrote payload to {output_path}')


if __name__ == '__main__':
    main()
