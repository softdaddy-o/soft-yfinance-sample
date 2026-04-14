#!/usr/bin/env python3
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / 'site' / 'data' / 'market-data.json'
OUTPUT_PATH = ROOT / 'site' / 'social-preview.png'

WIDTH = 1200
HEIGHT = 630

BG_TOP = '#08131d'
BG_BOTTOM = '#040a10'
PANEL = (10, 24, 39, 228)
BORDER = (130, 187, 233, 58)
TEXT = '#ebf6ff'
MUTED = '#93b4cd'
ACCENT = '#76d3ff'
POSITIVE = '#6ef1c2'
NEGATIVE = '#ff7f90'


def load_font(size, bold=False):
    candidates = []
    if bold:
        candidates.extend([
            'C:/Windows/Fonts/segoeuib.ttf',
            'C:/Windows/Fonts/arialbd.ttf',
        ])
    candidates.extend([
        'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/arial.ttf',
    ])

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT_SMALL = load_font(22)
FONT_BODY = load_font(28)
FONT_LABEL = load_font(24, bold=True)
FONT_H1 = load_font(62, bold=True)
FONT_H2 = load_font(36, bold=True)
FONT_PRICE = load_font(34, bold=True)


def lerp_color(start, end, steps, index):
    if steps <= 1:
        return start
    ratio = index / (steps - 1)
    return tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(3))


def draw_vertical_gradient(image):
    draw = ImageDraw.Draw(image)
    start = (8, 19, 29)
    end = (4, 10, 16)
    for y in range(HEIGHT):
        color = lerp_color(start, end, HEIGHT, y)
        draw.line([(0, y), (WIDTH, y)], fill=color)


def rounded_panel(base, box, radius=28):
    panel = Image.new('RGBA', (box[2] - box[0], box[3] - box[1]), PANEL)
    border = Image.new('RGBA', panel.size, (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle((0, 0, panel.size[0] - 1, panel.size[1] - 1), radius=radius, outline=BORDER, width=1)
    base.alpha_composite(panel, box[:2])
    base.alpha_composite(border, box[:2])


def price_text(quote):
    currency = quote.get('currency') or ''
    value = quote.get('price')
    if value is None:
        return 'N/A'
    if currency == 'USD':
        return f'${value:,.2f}'
    if currency == 'KRW':
        return f'₩{int(value):,}'
    if currency == 'JPY':
        return f'¥{int(value):,}'
    if currency == 'EUR':
        return f'€{value:,.2f}'
    if currency == 'INR':
        return f'₹{value:,.2f}'
    return f'{value:,.2f} {currency}'.strip()


def change_text(quote):
    value = quote.get('changePercent')
    if value is None:
        return 'N/A'
    sign = '+' if value > 0 else ''
    return f'{sign}{value:.2f}%'


def draw_sparkline(draw, box, history, positive):
    if not history or len(history) < 2:
        return

    min_value = min(history)
    max_value = max(history)
    span = max_value - min_value or 1

    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    step_x = width / (len(history) - 1)

    points = []
    for index, value in enumerate(history):
        x = left + index * step_x
        y = bottom - ((value - min_value) / span) * height
        points.append((x, y))

    color = POSITIVE if positive else NEGATIVE
    draw.line(points, fill=color, width=4, joint='curve')


def pick_quotes(payload):
    preferred = ['AAPL', '005930.KS', 'BTC-USD']
    all_quotes = []
    for group in payload.get('marketUniverses', []):
        all_quotes.extend(group.get('quotes', []))

    selected = []
    for symbol in preferred:
        match = next((quote for quote in all_quotes if quote.get('symbol') == symbol), None)
        if match:
            selected.append(match)

    return selected[:3]


def render():
    payload = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    canvas = Image.new('RGBA', (WIDTH, HEIGHT))
    draw_vertical_gradient(canvas)
    draw = ImageDraw.Draw(canvas)

    draw.text((66, 54), 'soft-yfinance-sample', font=FONT_LABEL, fill=ACCENT)
    draw.text((66, 92), 'Global market graphs from yfinance', font=FONT_H1, fill=TEXT)
    draw.text(
        (66, 176),
        'Static GitHub Pages dashboard with multi-market quotes, bulk downloads, search, screeners, deep dives, and richer yfinance coverage.',
        font=FONT_BODY,
        fill=MUTED,
    )

    stats = payload.get('summaryStats', {})
    stat_y = 252
    stat_boxes = [
        ('Feature Tests', str(stats.get('featureTests', 'N/A'))),
        ('Market Groups', str(stats.get('marketGroups', 'N/A'))),
        ('Deep Dives', str(stats.get('deepDives', 'N/A'))),
    ]

    x = 66
    for label, value in stat_boxes:
        rounded_panel(canvas, (x, stat_y, x + 158, stat_y + 86), radius=24)
        draw.text((x + 16, stat_y + 16), label, font=FONT_SMALL, fill=MUTED)
        draw.text((x + 16, stat_y + 42), value, font=FONT_H2, fill=TEXT)
        x += 176

    quotes = pick_quotes(payload)
    card_top = 360
    card_width = 338
    gap = 24

    for index, quote in enumerate(quotes):
        left = 66 + index * (card_width + gap)
        box = (left, card_top, left + card_width, 576)
        rounded_panel(canvas, box, radius=28)

        positive = (quote.get('change') or 0) >= 0
        draw.text((left + 22, card_top + 20), quote.get('symbol', 'N/A'), font=FONT_LABEL, fill=ACCENT)
        draw.text((left + 22, card_top + 54), quote.get('name', 'N/A')[:22], font=FONT_SMALL, fill=TEXT)
        draw.text((left + 22, card_top + 88), price_text(quote), font=FONT_PRICE, fill=TEXT)
        draw.text((left + 22, card_top + 130), change_text(quote), font=FONT_LABEL, fill=POSITIVE if positive else NEGATIVE)
        draw.text((left + 22, card_top + 164), f"{quote.get('assetType', 'UNKNOWN')} - {quote.get('exchange', 'N/A')}", font=FONT_SMALL, fill=MUTED)
        draw_sparkline(draw, (left + 18, card_top + 194, left + card_width - 18, card_top + 214), quote.get('history', []), positive)

    draw.text((66, 592), 'https://softdaddy-o.github.io/soft-yfinance-sample/', font=FONT_SMALL, fill=MUTED)
    canvas.convert('RGB').save(OUTPUT_PATH, quality=95)


if __name__ == '__main__':
    render()
