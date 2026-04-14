async function loadData() {
    const response = await fetch('./data/market-data.json', { cache: 'no-store' });
    if (!response.ok) {
        throw new Error(`Failed to load data: ${response.status}`);
    }
    return response.json();
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function cellText(value) {
    if (Array.isArray(value)) {
        return value.join(', ');
    }
    if (value && typeof value === 'object') {
        return JSON.stringify(value);
    }
    return value ?? '';
}

function formatNumber(value, currency) {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return 'N/A';
    }

    try {
        if (currency) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency,
                maximumFractionDigits: Math.abs(value) >= 1000 ? 0 : 2,
            }).format(value);
        }
        return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
    } catch (error) {
        return Number(value).toLocaleString('en-US');
    }
}

function formatCompact(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return 'N/A';
    }
    return new Intl.NumberFormat('en-US', {
        notation: 'compact',
        maximumFractionDigits: 2,
    }).format(value);
}

function formatPercent(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return 'N/A';
    }
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

function formatDate(value) {
    if (!value) {
        return 'N/A';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return escapeHtml(value);
    }
    return date.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
}

function buildSparkline(history, positive) {
    if (!Array.isArray(history) || history.length < 2) {
        return '';
    }

    const min = Math.min(...history);
    const max = Math.max(...history);
    const range = max - min || 1;
    const stepX = 140 / (history.length - 1);
    const points = history.map((value, index) => {
        const x = index * stepX;
        const y = 42 - ((value - min) / range) * 34;
        return `${x},${y}`;
    }).join(' ');

    return `
        <svg class="sparkline" viewBox="0 0 140 42" preserveAspectRatio="none" role="img" aria-label="Price history">
            <polyline points="${points}" class="${positive ? 'sparkline-positive' : 'sparkline-negative'}"></polyline>
        </svg>
    `;
}

function renderTable(records, title) {
    if (!records || records.length === 0) {
        return `<div class="empty-box">No ${escapeHtml(title)} data.</div>`;
    }

    const columns = Object.keys(records[0]);
    if (columns.length === 0) {
        return `<div class="empty-box">No ${escapeHtml(title)} data.</div>`;
    }
    const header = columns.map((column) => `<th>${escapeHtml(column)}</th>`).join('');
    const rows = records.map((record) => `
        <tr>
            ${columns.map((column) => `<td>${escapeHtml(cellText(record[column]))}</td>`).join('')}
        </tr>
    `).join('');

    return `
        <div class="table-wrap">
            <table class="data-table">
                <thead><tr>${header}</tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

function quoteCard(quote) {
    const positive = (quote.change ?? 0) >= 0;
    return `
        <article class="quote-card">
            <div class="quote-head">
                <div>
                    <p class="symbol">${escapeHtml(quote.symbol)}</p>
                    <h3>${escapeHtml(quote.name || quote.symbol)}</h3>
                    <p class="subtle">${escapeHtml(quote.assetType || 'UNKNOWN')} - ${escapeHtml(quote.exchange || 'N/A')}</p>
                </div>
                <span class="status-pill ${positive ? 'status-ok' : 'status-warn'}">${escapeHtml(formatPercent(quote.changePercent))}</span>
            </div>
            <p class="price-line">${escapeHtml(formatNumber(quote.price, quote.currency))}</p>
            <div class="sparkline-shell">${buildSparkline(quote.history || [], positive)}</div>
            <dl class="mini-stats">
                <div><dt>Prev</dt><dd>${escapeHtml(formatNumber(quote.previousClose, quote.currency))}</dd></div>
                <div><dt>Day</dt><dd>${escapeHtml(formatNumber(quote.dayLow, quote.currency))} - ${escapeHtml(formatNumber(quote.dayHigh, quote.currency))}</dd></div>
                <div><dt>52w</dt><dd>${escapeHtml(formatNumber(quote.fiftyTwoWeekLow, quote.currency))} - ${escapeHtml(formatNumber(quote.fiftyTwoWeekHigh, quote.currency))}</dd></div>
                <div><dt>Mkt Cap</dt><dd>${escapeHtml(formatCompact(quote.marketCap))}</dd></div>
            </dl>
        </article>
    `;
}

function renderSummaryStats(stats) {
    const mapping = [
        ['Feature Tests', stats.featureTests],
        ['Market Groups', stats.marketGroups],
        ['Instruments', stats.instrumentCount],
        ['Deep Dives', stats.deepDives],
    ];

    document.getElementById('summary-stats').innerHTML = mapping.map(([label, value]) => `
        <div class="stat-card">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
        </div>
    `).join('');
}

function renderMeta(payload) {
    document.getElementById('mode-badge').textContent = payload.mode || 'unknown';
    document.getElementById('generated-at').textContent = formatDate(payload.generatedAt);
    document.getElementById('library-version').textContent = payload.libraryVersion || 'unknown';
    document.getElementById('notes').innerHTML = (payload.notes || []).map((note) => `<p>${escapeHtml(note)}</p>`).join('');
}

function renderCoverage(features) {
    document.getElementById('coverage-grid').innerHTML = features.map((item) => `
        <article class="coverage-card">
            <div class="coverage-head">
                <h3>${escapeHtml(item.feature)}</h3>
                <span class="status-pill status-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span>
            </div>
            <p class="subtle">Sample: ${escapeHtml(item.sample)}</p>
            <p>${escapeHtml(item.note)}</p>
        </article>
    `).join('');
}

function renderUniverses(groups) {
    document.getElementById('universe-sections').innerHTML = groups.map((group) => `
        <article class="panel-card">
            <div class="section-heading compact">
                <h3>${escapeHtml(group.title)}</h3>
                <p>${escapeHtml(group.description)}</p>
            </div>
            <div class="quote-grid">${group.quotes.map(quoteCard).join('')}</div>
        </article>
    `).join('');
}

function renderBatchQuotes(batchQuotes) {
    document.getElementById('batch-quotes').innerHTML = batchQuotes.quotes.map(quoteCard).join('');
}

function renderBulkDownload(download) {
    const records = download.rows.map((row) => ({ date: row.date, ...row.values }));
    document.getElementById('bulk-download').innerHTML = renderTable(records, 'download');
}

function renderSearchLabs(searchLabs) {
    document.getElementById('search-labs').innerHTML = searchLabs.map((lab) => `
        <article class="info-card">
            <h4>${escapeHtml(lab.query)}</h4>
            <p class="subtle">${escapeHtml(lab.label)}</p>
            <dl class="mini-stats single-column">
                <div><dt>Stocks</dt><dd>${escapeHtml(lab.lookupCounts.stock)}</dd></div>
                <div><dt>ETFs</dt><dd>${escapeHtml(lab.lookupCounts.etf)}</dd></div>
                <div><dt>Indexes</dt><dd>${escapeHtml(lab.lookupCounts.index)}</dd></div>
            </dl>
            ${renderTable(lab.topResults, 'search results')}
        </article>
    `).join('');
}

function renderScreeners(screeners) {
    document.getElementById('screeners').innerHTML = screeners.map((item) => `
        <article class="info-card">
            <h4>${escapeHtml(item.title || item.name)}</h4>
            <p>${escapeHtml(item.description || '')}</p>
            ${renderTable(item.quotes, 'screener quotes')}
        </article>
    `).join('');
}

function renderMarketOverviews(markets) {
    document.getElementById('market-overviews').innerHTML = markets.map((market) => `
        <article class="info-card">
            <div class="coverage-head">
                <h4>${escapeHtml(market.code)}</h4>
                <span class="status-pill status-ok">${escapeHtml(market.status || 'unknown')}</span>
            </div>
            <p class="subtle">${escapeHtml(market.message || '')}</p>
            ${renderTable(market.entries, 'market overview')}
        </article>
    `).join('');
}

function renderSectorIndustry(data) {
    const sectorData = data.sector || { overview: {}, topCompanies: [], industries: [], name: 'Sector' };
    const industryData = data.industry || { overview: {}, topCompanies: [], topGrowthCompanies: [], name: 'Industry' };
    const sector = `
        <article class="info-card">
            <h4>${escapeHtml(sectorData.name)}</h4>
            <p>${escapeHtml(sectorData.overview.description || '')}</p>
            ${renderTable(sectorData.topCompanies, 'sector companies')}
            ${renderTable(sectorData.industries, 'sector industries')}
        </article>
    `;

    const industry = `
        <article class="info-card">
            <h4>${escapeHtml(industryData.name)}</h4>
            <p>${escapeHtml(industryData.overview.description || '')}</p>
            ${renderTable(industryData.topCompanies, 'industry companies')}
            ${renderTable(industryData.topGrowthCompanies, 'growth companies')}
        </article>
    `;

    document.getElementById('sector-industry').innerHTML = sector + industry;
}

function renderDeepDives(dives) {
    document.getElementById('deep-dive-list').innerHTML = dives.map((dive) => `
        <details class="detail-card" ${dive.symbol === 'AAPL' ? 'open' : ''}>
            <summary>
                <div>
                    <p class="symbol">${escapeHtml(dive.symbol)}</p>
                    <h3>${escapeHtml(dive.title)}</h3>
                    <p class="subtle">${escapeHtml(dive.assetType)}</p>
                </div>
                <span>${escapeHtml(formatNumber(dive.quote.price, dive.quote.currency))}</span>
            </summary>
            <div class="detail-grid">
                <article class="info-card">
                    <h4>Quote Snapshot</h4>
                    ${quoteCard(dive.quote)}
                </article>
                <article class="info-card">
                    <h4>Highlights</h4>
                    ${renderTable([dive.highlights], 'highlights')}
                </article>
                <article class="info-card">
                    <h4>Price History</h4>
                    ${renderTable(dive.historyRows, 'price history')}
                </article>
                <article class="info-card">
                    <h4>Calendar</h4>
                    ${renderTable([dive.calendar || {}], 'calendar')}
                </article>
                <article class="info-card">
                    <h4>Income Statement</h4>
                    ${renderTable(dive.financials.incomeStatement, 'income statement')}
                </article>
                <article class="info-card">
                    <h4>Balance Sheet</h4>
                    ${renderTable(dive.financials.balanceSheet, 'balance sheet')}
                </article>
                <article class="info-card">
                    <h4>Cashflow</h4>
                    ${renderTable(dive.financials.cashflow, 'cashflow')}
                </article>
                <article class="info-card">
                    <h4>Research</h4>
                    ${renderTable(dive.research.earningsDates, 'earnings dates')}
                    ${renderTable(dive.research.recommendations, 'recommendations')}
                    ${renderTable([dive.research.analystTargets || {}], 'analyst targets')}
                </article>
                <article class="info-card">
                    <h4>Ownership</h4>
                    ${renderTable(dive.ownership.majorHolders, 'major holders')}
                    ${renderTable(dive.ownership.institutionalHolders, 'institutional holders')}
                </article>
                <article class="info-card">
                    <h4>Insiders</h4>
                    ${renderTable(dive.ownership.insiderTransactions, 'insider transactions')}
                    ${renderTable(dive.ownership.insiderPurchases, 'insider purchases')}
                </article>
                <article class="info-card">
                    <h4>Filings And News</h4>
                    ${renderTable(dive.filings, 'filings')}
                    ${renderTable(dive.news, 'news')}
                </article>
                <article class="info-card">
                    <h4>Options / Fund Data</h4>
                    ${dive.options?.available ? renderTable(dive.options.calls, 'option calls') : `<div class="empty-box">${escapeHtml(dive.options?.note || 'No options data.')}</div>`}
                    ${renderTable(dive.fundData?.topHoldings || [], 'fund holdings')}
                </article>
            </div>
        </details>
    `).join('');
}

function renderError(message) {
    document.body.innerHTML = `<main class="page-shell"><div class="empty-box">${escapeHtml(message)}</div></main>`;
}

async function main() {
    try {
        const payload = await loadData();
        renderSummaryStats(payload.summaryStats || {});
        renderMeta(payload);
        renderCoverage(payload.featureCoverage || []);
        renderUniverses(payload.marketUniverses || []);
        renderBatchQuotes(payload.batchQuotes || { quotes: [] });
        renderBulkDownload(payload.bulkDownload || { rows: [] });
        renderSearchLabs(payload.searchLabs || []);
        renderScreeners(payload.screeners || []);
        renderMarketOverviews(payload.marketOverviews || []);
        renderSectorIndustry(payload.sectorIndustry || { sector: {}, industry: {} });
        renderDeepDives(payload.deepDives || []);
    } catch (error) {
        console.error(error);
        renderError(error.message);
    }
}

main();
