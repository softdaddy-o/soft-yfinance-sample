async function loadQuotes() {
    const response = await fetch('./data/market-data.json', { cache: 'no-store' });
    if (!response.ok) {
        throw new Error(`Failed to load data: ${response.status}`);
    }
    return response.json();
}

function formatNumber(value, currency) {
    if (value === null || value === undefined) {
        return 'N/A';
    }

    const usesCurrency = typeof currency === 'string' && currency.length > 0;
    const options = usesCurrency
        ? { style: 'currency', currency, maximumFractionDigits: value >= 1000 ? 0 : 2 }
        : { maximumFractionDigits: value >= 1000 ? 0 : 2 };

    try {
        return new Intl.NumberFormat('en-US', options).format(value);
    } catch (error) {
        return Number(value).toLocaleString('en-US');
    }
}

function formatCompactNumber(value) {
    if (value === null || value === undefined) {
        return 'N/A';
    }

    return new Intl.NumberFormat('en-US', {
        notation: 'compact',
        maximumFractionDigits: 2,
    }).format(value);
}

function formatChange(change, changePercent, currency) {
    if (change === null || change === undefined || changePercent === null || changePercent === undefined) {
        return 'N/A';
    }

    const sign = change > 0 ? '+' : '';
    return `${sign}${formatNumber(change, currency)} (${sign}${changePercent.toFixed(2)}%)`;
}

function buildSparkline(history, isPositive) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 180 52');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('class', 'sparkline');

    if (!Array.isArray(history) || history.length < 2) {
        return svg;
    }

    const min = Math.min(...history);
    const max = Math.max(...history);
    const range = max - min || 1;
    const stepX = 180 / (history.length - 1);

    const points = history.map((value, index) => {
        const x = index * stepX;
        const y = 48 - ((value - min) / range) * 44;
        return `${x},${y}`;
    }).join(' ');

    const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    polyline.setAttribute('fill', 'none');
    polyline.setAttribute('stroke', isPositive ? '#5af0b3' : '#ff7d86');
    polyline.setAttribute('stroke-width', '3');
    polyline.setAttribute('stroke-linecap', 'round');
    polyline.setAttribute('stroke-linejoin', 'round');
    polyline.setAttribute('points', points);

    svg.appendChild(polyline);
    return svg;
}

function renderQuoteCard(quote) {
    const template = document.getElementById('quote-card-template');
    const fragment = template.content.cloneNode(true);

    fragment.querySelector('.symbol').textContent = quote.symbol;
    fragment.querySelector('.name').textContent = quote.name || quote.symbol;
    fragment.querySelector('.quote-type').textContent = quote.quoteType || 'UNKNOWN';
    fragment.querySelector('.price').textContent = formatNumber(quote.price, quote.currency);
    fragment.querySelector('.previous-close').textContent = formatNumber(quote.previousClose, quote.currency);
    fragment.querySelector('.day-range').textContent = `${formatNumber(quote.dayLow, quote.currency)} - ${formatNumber(quote.dayHigh, quote.currency)}`;
    fragment.querySelector('.market-cap').textContent = formatCompactNumber(quote.marketCap);
    fragment.querySelector('.exchange').textContent = quote.exchange || 'N/A';

    const changePill = fragment.querySelector('.change-pill');
    const isPositive = (quote.change || 0) >= 0;
    changePill.textContent = formatChange(quote.change, quote.changePercent, quote.currency);
    changePill.classList.add(
        quote.change === null || quote.change === undefined
            ? 'flat'
            : isPositive
                ? 'positive'
                : 'negative'
    );

    const sparklineWrap = fragment.querySelector('.sparkline-wrap');
    const originalSparkline = fragment.querySelector('.sparkline');
    sparklineWrap.replaceChild(buildSparkline(quote.history, isPositive), originalSparkline);

    return fragment;
}

function setHeader(payload) {
    document.getElementById('mode-badge').textContent = payload.mode || 'unknown';
    document.getElementById('data-source').textContent = payload.source || 'unknown';

    const generatedAt = payload.generatedAt
        ? new Date(payload.generatedAt).toLocaleString('en-US', {
            dateStyle: 'medium',
            timeStyle: 'short',
        })
        : 'N/A';

    document.getElementById('generated-at').textContent = generatedAt;
}

function renderEmptyState(message) {
    const grid = document.getElementById('quote-grid');
    grid.innerHTML = `<div class="empty-state">${message}</div>`;
}

async function main() {
    try {
        const payload = await loadQuotes();
        setHeader(payload);

        const grid = document.getElementById('quote-grid');
        grid.innerHTML = '';

        if (!payload.quotes || payload.quotes.length === 0) {
            renderEmptyState('No quotes were generated.');
            return;
        }

        payload.quotes.forEach((quote) => {
            grid.appendChild(renderQuoteCard(quote));
        });
    } catch (error) {
        renderEmptyState(error.message);
        console.error(error);
    }
}

main();
