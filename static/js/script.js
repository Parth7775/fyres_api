// Dashboard Logic

// Load positions and algo status on startup
document.addEventListener('DOMContentLoaded', () => {
    fetchPositions();
    fetchAlgoStatus();
    fetchPositions();
    fetchAlgoStatus();
    fetchHistory();
    // Auto refresh every 5 seconds
    setInterval(fetchPositions, 5000);
    setInterval(fetchHistory, 5000); // Poll history too
    setInterval(fetchAlgoStatus, 1000); // Polling Algo status (1s)
});

async function fetchPositions() {
    try {
        const response = await fetch('/api/positions');
        const data = await response.json();

        const container = document.getElementById('positions-container');
        const statusBadge = document.getElementById('connection-status');

        statusBadge.textContent = "Connected";
        statusBadge.style.color = "var(--success-color)";
        statusBadge.style.backgroundColor = "rgba(76, 175, 80, 0.1)";

        if (!data.positions || data.positions.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px;">No open positions</p>';
            updateTotalPnL(0);
            return;
        }

        // Split Positions
        const realPositions = data.positions.filter(p => p.productType !== "PAPER (Sim)" && p.productType !== "PAPER");
        const paperPositions = data.positions.filter(p => p.productType === "PAPER (Sim)" || p.productType === "PAPER");

        let html = '';
        let totalPnL = 0;

        // 1. REAL POSITIONS
        if (realPositions.length > 0) {
            html += '<h4 style="margin: 10px 0; color: var(--accent-color);">Live Positions (Broker)</h4>';
            html += generateTable(realPositions);
            // Calculate Total Real P&L
            realPositions.forEach(p => totalPnL += parseFloat(p.pl));
        }

        // 2. PAPER POSITIONS
        if (paperPositions.length > 0) {
            html += '<h4 style="margin: 15px 0 10px 0; color: #aaa; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px;">Simulation / Paper Trades</h4>';
            html += generateTable(paperPositions);
            // (Optional) Add Paper P&L to total? User usually acts separate.
            // Let's NOT add paper PnL to the Main Counter.
        }

        if (realPositions.length === 0 && paperPositions.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px;">No open positions</p>';
        } else {
            container.innerHTML = html;
        }

        updateTotalPnL(totalPnL);

    } catch (error) {
        console.error('Error fetching positions:', error);
        document.getElementById('connection-status').textContent = "Connection Error";
        document.getElementById('connection-status').style.color = "var(--error-color)";
    }
}

function generateTable(positions) {
    let html = `
        <table class="algo-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>Avg Price</th>
                    <th>LTP</th>
                    <th>P&L</th>
                    <th>Type</th>
                </tr>
            </thead>
            <tbody>
    `;
    positions.forEach(pos => {
        const pnl = parseFloat(pos.pl);
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';
        const ltp = parseFloat(pos.ltp);
        html += `
            <tr>
                <td style="font-weight: 500;">${pos.symbol}</td>
                <td>${pos.netQty}</td>
                <td>${parseFloat(pos.avgPrice).toFixed(2)}</td>
                <td>${ltp ? ltp.toFixed(2) : '-'}</td>
                <td class="pnl-value ${pnlClass}">${pnl.toFixed(2)}</td>
                <td><span class="tag tag-tracking">${pos.productType}</span></td>
            </tr>
        `;
    });
    html += '</tbody></table>';
    return html;
}

// ------ History Logic ------
async function fetchHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        const tbody = document.getElementById('history-body');

        // Update Header to match new columns
        const thead = document.querySelector("#history-container thead tr");
        if (thead) {
            thead.innerHTML = `
                <th>Symbol</th>
                <th>Side</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>PnL</th>
                <th>Status</th>
            `;
        }

        if (!data.history || data.history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#666;">No trades recorded.</td></tr>';
            return;
        }

        // 1. Filter for TODAY's trades only
        // Format: YYYY-MM-DD
        const todayStr = new Date().toISOString().split('T')[0];
        // We can check if any timestamp starts with todayStr
        // OR rely on user intent "only todays trade". 
        // Let's filter strictly.
        // NOTE: Server might be in different timezone, but assuming local consistency for now.
        // Better: Check if row.Timestamp contains todayStr.

        let todaysRows = data.history.filter(row => row.Timestamp && row.Timestamp.startsWith(todayStr));

        if (todaysRows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#666;">No trades for today (' + todayStr + ').</td></tr>';
            return;
        }

        // 2. Consolidate Trades (Group Entry & Exit)
        // History is typically newest first -> oldest last (or vice versa).
        // The API reverses it? "clean_history.reverse()". So Newest First.
        // To build trades properly, it's easier to process Oldest -> Newest.

        // Working set (Oldest to Newest)
        const chronoRows = [...todaysRows].reverse();

        let trades = [];
        let openPositions = {}; // Map symbol -> partial trade object

        chronoRows.forEach(row => {
            const sym = row.Symbol;
            const action = row.Action || "";
            const price = parseFloat(row.Price);
            const ts = row.Timestamp.split(' ')[1] || row.Timestamp; // Just Time for display? User asked for Date also previously, but if we filter for today, maybe just time is cleaner? Or show full? User said "show date also" previously. Let's keep Time only for compactness if verified Today? OR Full. Let's show Time for Entry/Exit columns to save space, header implies Today.

            // Actually, let's keep it simple: Show Time. Since filter is Today.

            if (action.includes("ENTRY") || action === "SELL" || action === "BUY") {
                // New Position
                // If we already have one open for this symbol? (Averaging not supported in simple view)
                // Just overwrite or stack? Let's assume one at a time per symbol for simplicity.
                openPositions[sym] = {
                    symbol: sym,
                    side: action.includes("SHORT") || action === "SELL" ? "SHORT" : "LONG",
                    entryTime: ts,
                    entryPrice: price,
                    exitTime: "-",
                    exitPrice: "-",
                    pnl: 0,
                    status: "OPEN",
                    product: row.Product
                };
            }
            else if (action.includes("EXIT") || action === "BUY" && openPositions[sym]?.side === "SHORT") {
                // Close Position
                if (openPositions[sym]) {
                    let trade = openPositions[sym];
                    trade.exitTime = ts;
                    trade.exitPrice = price;
                    trade.status = "CLOSED";

                    // Calc PnL logic if not provided in product string
                    // Usually Product string has "PnL: xxx"
                    // Parse PnL from Product string if available
                    let pnlMatch = (row.Product || "").match(/PnL:\s*(-?[\d\.]+)/);
                    if (pnlMatch) {
                        trade.pnl = parseFloat(pnlMatch[1]);
                    } else {
                        // Estimate
                        if (trade.side === "SHORT") {
                            trade.pnl = (trade.entryPrice - price) * (row.Qty || 1);
                        } else {
                            trade.pnl = (price - trade.entryPrice) * (row.Qty || 1);
                        }
                    }

                    // Specific Exit Reason
                    if (action.includes("SL")) trade.status = "SL HIT";
                    if (action.includes("TIME")) trade.status = "TIME EXIT";
                    if (action.includes("TARGET")) trade.status = "TARGET";

                    trades.push(trade);
                    delete openPositions[sym];
                } else {
                    // Orphan exit (Entry happened before today?)
                    // Ignore or log?
                }
            }
        });

        // Add remaining open positions
        Object.values(openPositions).forEach(t => trades.push(t));

        // Render Trades (Newest First)
        trades.reverse();

        let html = '';
        trades.forEach(t => {
            const pnlVal = parseFloat(t.pnl);
            const pnlClass = t.status === "OPEN" ? "tag-tracking" : (pnlVal >= 0 ? "positive" : "negative");
            const pnlDisplay = t.status === "OPEN" ? "Running" : pnlVal.toFixed(2);

            // Clean Symbol
            const displaySym = t.symbol.replace('NSE:', '');

            html += `
                <tr>
                    <td style="font-weight:500">${displaySym}</td>
                    <td><span class="tag ${t.side === 'SHORT' ? 'tag-pe' : 'tag-ce'}">${t.side}</span></td>
                    <td>${t.entryPrice} <span style="font-size:0.8em; color:#666">@ ${t.entryTime}</span></td>
                    <td>${t.exitPrice} <span style="font-size:0.8em; color:#666">${t.exitTime !== '-' ? '@ ' + t.exitTime : ''}</span></td>
                    <td class="${pnlClass}" style="font-weight:600">${pnlDisplay}</td>
                    <td><span class="tag" style="background:rgba(0,0,0,0.05); color:var(--text-secondary)">${t.status}</span></td>
                </tr>
            `;
        });

        tbody.innerHTML = html;

    } catch (e) {
        console.warn("History fetch error", e);
    }
}

function updateTotalPnL(val) {
    const el = document.getElementById('total-pnl-value');
    if (el) {
        el.textContent = val.toFixed(2);
        if (val >= 0) {
            el.className = 'positive';
        } else {
            el.className = 'negative';
        }
    }
}

// ------ Algo Monitor Logic ------

async function fetchAlgoStatus() {
    try {
        // Fetch from memory API (No Cache)
        const response = await fetch('/api/live_data');
        if (!response.ok) throw new Error("API Error");

        const data = await response.json();

        const container = document.getElementById('algo-container');
        const timeEl = document.getElementById('algo-timestamp');

        if (timeEl && data.timestamp) {
            timeEl.innerHTML = 'Last Update: ' + data.timestamp + ' <span style="display:inline-block; width:8px; height:8px; background-color:#4caf50; border-radius:50%; margin-left:5px; box-shadow: 0 0 5px #4caf50;"></span>';
        }

        if (!data.scan_results || data.scan_results.length === 0) {
            // Only show Initializing if we have NO data yet.
            if (!container.innerHTML.includes("<table")) {
                container.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">Initializing (Waiting for data)...</p>';
            } else {
                // If we have data but API returned empty, mark as Stale
                if (timeEl) timeEl.innerHTML = 'Last Update: ' + data.timestamp + ' <span style="display:inline-block; width:8px; height:8px; background-color:#ff9800; border-radius:50%; margin-left:5px; box-shadow: 0 0 5px #ff9800;" title="Stale Data / Reconnecting"></span>';
            }
            return;
        }

        let html = `
            <table class="algo-table">
                <thead>
                    <tr>
                        <th>Strike</th>
                        <th>Type</th>
                        <th>Prices</th>
                        <th>RSI</th>
                        <th>Signal</th>
                        <th>State</th>
                    </tr>
                </thead>
                <tbody>
        `;

        // Sort: Active first, then others
        const sortedResults = data.scan_results.sort((a, b) => {
            return (b.is_active === true) - (a.is_active === true);
        });

        sortedResults.forEach(item => {
            const isCall = item.type === "CE";
            const typeClass = isCall ? "tag-ce" : "tag-pe";

            let statusBadge = `<span class="tag tag-tracking">Tracking</span>`;
            if (item.is_active) {
                statusBadge = `<span class="tag tag-active">ACTIVE</span>`;
            }

            let actionText = item.action || "HOLD";
            let rowClass = "";
            if (item.action === "ENTER_SHORT") {
                rowClass = "signal-triggered";
                actionText = "⚠️ BREAKDOWN";
            }

            // Format symbol to be shorter? (NSE:NIFTY26FEB...)
            // Just show Strike Code if possible, or full symbol
            const displaySymbol = item.symbol.replace('NSE:', '');

            // LTP
            const ltpDisplay = item.ltp > 0 ? item.ltp.toFixed(1) : '-';

            html += `
                <tr class="${rowClass}">
                    <td style="font-weight: 500;">${displaySymbol}</td>
                    <td class="${typeClass}">${item.type}</td>
                    <td>₹${ltpDisplay}</td>
                    <td style="font-weight: 600; color: ${item.rsi > 70 ? '#ffb74d' : 'var(--text-primary)'}">${item.rsi}</td>
                    <td>${actionText}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;

        // Update Watchlist Sidebar
        updateWatchlist(data.scan_results);

    } catch (error) {
        console.warn("Algo status fetch failed (script might not be running):", error);
        document.getElementById('algo-timestamp').textContent = "Offline";
    }
}

function updateWatchlist(scanResults) {
    const container = document.getElementById('watchlist-items');
    if (!container) return;

    if (!scanResults || scanResults.length === 0) {
        container.innerHTML = '<div style="padding: 15px; text-align: center; color: var(--text-secondary);">No active symbols</div>';
        return;
    }

    // Sort: Active first
    const sorted = [...scanResults].sort((a, b) => (b.is_active === true) - (a.is_active === true));

    let html = '';
    sorted.forEach(item => {
        const symbol = item.symbol.replace('NSE:', '');
        const isCall = item.type === "CE";
        const ltp = item.ltp > 0 ? item.ltp.toFixed(2) : '-';
        const rsiColor = item.rsi > 70 ? '#ffb74d' : '#888';

        // Dynamic Class for Price Change (Simulation) -> In real app, we need prev close. 
        // For now, just grey/white.

        const activeClass = item.is_active ? 'border-left: 3px solid var(--accent-color); background: rgba(255, 255, 255, 0.05);' : '';

        html += `
            <div style="padding: 10px 15px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; ${activeClass}">
                <div>
                    <div style="font-weight: 500; font-size: 13px; color: #e1e1e1;">${symbol}</div>
                    <div style="font-size: 11px; color: ${isCall ? 'var(--success-color)' : 'var(--error-color)'}; margin-top: 2px;">${item.type}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 600; font-size: 13px;">${ltp}</div>
                    <div style="font-size: 10px; color: ${rsiColor}; margin-top: 2px;">RSI: ${item.rsi}</div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}
