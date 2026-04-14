#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_SYMBOLS = ['AAPL', 'MSFT', 'NVDA', 'BTC-USD', '005930.KS']

DEMO_QUOTES = {
    'AAPL': {
        'name': 'Apple Inc.',
        'quoteType': 'EQUITY',
        'currency': 'USD',
        'exchange': 'NMS',
        'price': 194.52,
        'previousClose': 192.80,
        'dayHigh': 195.18,
        'dayLow': 191.94,
        'marketCap': 2984000000000,
        'history': [189.42, 190.33, 191.78, 192.80, 194.52],
    },
    'MSFT': {
        'name': 'Microsoft Corporation',
        'quoteType': 'EQUITY',
        'currency': 'USD',
        'exchange': 'NMS',
        'price': 431.12,
        'previousClose': 428.95,
        'dayHigh': 432.04,
        'dayLow': 427.80,
        'marketCap': 3201000000000,
        'history': [422.84, 425.21, 426.44, 428.95, 431.12],
    },
    'NVDA': {
        'name': 'NVIDIA Corporation',
        'quoteType': 'EQUITY',
        'currency': 'USD',
        'exchange': 'NMS',
        'price': 118.77,
        'previousClose': 116.41,
        'dayHigh': 119.06,
        'dayLow': 115.82,
        'marketCap': 2897000000000,
        'history': [111.15, 112.62, 114.90, 116.41, 118.77],
    },
    'BTC-USD': {
        'name': 'Bitcoin USD',
        'quoteType': 'CRYPTOCURRENCY',
        'currency': 'USD',
        'exchange': 'CCC',
        'price': 83920.44,
        'previousClose': 82774.31,
        'dayHigh': 84211.10,
        'dayLow': 82195.27,
        'marketCap': None,
        'history': [81124.44, 81750.10, 82488.32, 82774.31, 83920.44],
    },
    '005930.KS': {
        'name': 'Samsung Electronics Co., Ltd.',
        'quoteType': 'EQUITY',
        'currency': 'KRW',
        'exchange': 'KSC',
        'price': 84300,
        'previousClose': 83600,
        'dayHigh': 84800,
        'dayLow': 83200,
        'marketCap': 503000000000000,
        'history': [82100, 82600, 83100, 83600, 84300],
    },
}


def parse_args():
    parser = argparse.ArgumentParser(description='Generate static market data from yfinance.')
    parser.add_argument('--symbols', nargs='+', default=DEFAULT_SYMBOLS, help='Ticker symbols to fetch.')
    parser.add_argument(
        '--output',
        default=str(Path(__file__).resolve().parent.parent / 'site' / 'data' / 'market-data.json'),
        help='Where to write the output JSON.',
    )
    parser.add_argument('--demo', action='store_true', help='Write bundled demo data instead of live data.')
    return parser.parse_args()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def demo_payload(symbols):
    quotes = []
    for symbol in symbols:
        base = DEMO_QUOTES.get(symbol)
        if not base:
            continue

        change = base['price'] - base['previousClose']
        change_percent = (change / base['previousClose']) * 100 if base['previousClose'] else None

        quotes.append(
            {
                'symbol': symbol,
                'name': base['name'],
                'quoteType': base['quoteType'],
                'currency': base['currency'],
                'exchange': base['exchange'],
                'price': base['price'],
                'previousClose': base['previousClose'],
                'change': round(change, 4),
                'changePercent': round(change_percent, 4) if change_percent is not None else None,
                'dayHigh': base['dayHigh'],
                'dayLow': base['dayLow'],
                'marketCap': base['marketCap'],
                'history': base['history'],
            }
        )

    return {
        'generatedAt': now_iso(),
        'mode': 'demo',
        'source': 'Bundled sample data',
        'quotes': quotes,
    }


def fetch_live_quotes(symbols):
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError('yfinance is not installed. Run `pip install -r requirements.txt`.') from exc

    quotes = []
    failures = []

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            history_df = ticker.history(period='5d', interval='1d', auto_adjust=False)
            history = []
            if not history_df.empty:
                history = [round(float(v), 4) for v in history_df['Close'].dropna().tolist()[-5:]]

            price = safe_float(info.get('regularMarketPrice'))
            previous_close = safe_float(info.get('regularMarketPreviousClose'))
            if price is None and history:
                price = history[-1]
            if previous_close is None and len(history) >= 2:
                previous_close = history[-2]

            change = None
            change_percent = None
            if price is not None and previous_close:
                change = price - previous_close
                change_percent = (change / previous_close) * 100

            quotes.append(
                {
                    'symbol': symbol,
                    'name': info.get('shortName') or info.get('longName') or symbol,
                    'quoteType': info.get('quoteType') or 'UNKNOWN',
                    'currency': info.get('currency'),
                    'exchange': info.get('fullExchangeName') or info.get('exchange'),
                    'price': price,
                    'previousClose': previous_close,
                    'change': round(change, 4) if change is not None else None,
                    'changePercent': round(change_percent, 4) if change_percent is not None else None,
                    'dayHigh': safe_float(info.get('dayHigh')),
                    'dayLow': safe_float(info.get('dayLow')),
                    'marketCap': safe_int(info.get('marketCap')),
                    'history': history,
                }
            )
        except Exception as exc:
            failures.append({'symbol': symbol, 'error': str(exc)})

    if not quotes:
        raise RuntimeError(f'All symbols failed: {json.dumps(failures, ensure_ascii=True)}')

    return {
        'generatedAt': now_iso(),
        'mode': 'live',
        'source': 'Yahoo Finance via yfinance',
        'quotes': quotes,
        'failures': failures,
    }


def write_json(output_path, payload):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    args = parse_args()
    output_path = Path(args.output).resolve()

    if args.demo:
        payload = demo_payload(args.symbols)
    else:
        payload = fetch_live_quotes(args.symbols)

    write_json(output_path, payload)
    print(f'Wrote {len(payload["quotes"])} quotes to {output_path}')


if __name__ == '__main__':
    main()
