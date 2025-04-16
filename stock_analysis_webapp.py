"""
Enhanced Stock Analysis Web Application with Advanced Features
- Modern UI with glassmorphism design
- Real-time updates
- Sector performance analysis
- Dark mode support
- Interactive sparkline charts
- Advanced filtering
- News integration
- Enhanced visualizations
"""

from flask import Flask, render_template, jsonify, send_from_directory
import requests
import json
import os
import time
from datetime import datetime, timedelta
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Create directories
os.makedirs('templates', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('static', exist_ok=True)

STOCK_LIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", 
    "TSLA", "NVDA", "JPM", "V", "WMT", 
    "DIS", "NFLX", "PYPL", "INTC", "AMD", 
    "BA", "PFE", "KO", "PEP", "XOM"
]

# Enhanced HTML template with modern UI elements
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Market Dashboard - Prathap's Analysis</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #212529;
            --card-bg: rgba(255, 255, 255, 0.9);
            --border-color: rgba(255, 255, 255, 0.3);
        }
        
        [data-theme="dark"] {
            --bg-color: #1a1a1a;
            --text-color: #ffffff;
            --card-bg: rgba(30, 30, 30, 0.9);
            --border-color: rgba(255, 255, 255, 0.1);
        }

        body {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            color: var(--text-color);
            transition: all 0.3s ease;
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }

        .stock-card {
            transition: transform 0.2s, box-shadow 0.2s;
            margin-bottom: 15px;
        }

        .stock-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        }

        /* Loading animations */
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .loading-pulse { animation: pulse 1.5s infinite; }

        /* Theme toggle */
        .theme-toggle {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <!-- Theme toggle -->
    <button class="theme-toggle btn btn-primary btn-sm" onclick="toggleTheme()">
        Toggle Dark Mode
    </button>

    <div class="container my-4">
        <h1 class="mb-2">Stock Market Dashboard <small class="text-muted">Prathap's Analysis</small></h1>
        
        <!-- Controls -->
        <div class="row mb-4 g-3">
            <div class="col-md-4">
                <input type="text" class="form-control" placeholder="Search stocks..." id="stockSearch">
            </div>
            <div class="col-md-3">
                <select class="form-select" id="sectorFilter">
                    <option value="">All Sectors</option>
                    <option value="Technology">Technology</option>
                    <option value="Financial Services">Financial Services</option>
                    <!-- Add other sectors dynamically -->
                </select>
            </div>
            <div class="col-md-3">
                <select class="form-select" id="recommendationFilter">
                    <option value="">All Recommendations</option>
                    <option value="BUY">Buy</option>
                    <option value="SELL">Sell</option>
                    <option value="HOLD">Hold</option>
                </select>
            </div>
            <div class="col-md-2">
                <button id="refreshBtn" class="btn btn-primary w-100">Refresh</button>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="row mb-4 g-4">
            <!-- Summary cards remain similar but with enhanced styling -->
        </div>

        <!-- Market Overview -->
        <div class="row mb-4 g-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Sector Performance</h5>
                        <div id="sectorChart" style="height: 300px;"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Market Heatmap</h5>
                        <div id="heatmap" style="height: 300px;"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Stock List -->
        <div id="stocksList" class="row row-cols-1 row-cols-md-2 g-4"></div>
    </div>

    <!-- JavaScript includes and code -->
    <script>
        // Theme management
        function toggleTheme() {
            document.body.setAttribute('data-theme',
                document.body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'
            );
        }
        
        // Real-time updates
        const eventSource = new EventSource('/api/stream');
        eventSource.onmessage = (e) => updateStocks(JSON.parse(e.data));
        
        // Enhanced stock card rendering with animations
        function renderStockCard(stock) {
            return `
                <div class="col">
                    <div class="card stock-card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start">
                                <div class="d-flex align-items-center">
                                    <img src="https://logo.clearbit.com/${stock.symbol.toLowerCase()}.com?size=40" 
                                         class="me-2 rounded-circle" 
                                         alt="${stock.symbol} logo"
                                         onerror="this.style.display='none'">
                                    <div>
                                        <h5 class="card-title mb-0">${stock.symbol}</h5>
                                        <small class="text-muted">${stock.sector || 'Sector N/A'}</small>
                                    </div>
                                </div>
                                <span class="badge bg-${stock.recommendation === 'BUY' ? 'success' : 'danger'}">
                                    ${stock.recommendation}
                                </span>
                            </div>
                            <!-- Add sparkline chart -->
                            <div class="mt-3" id="sparkline-${stock.symbol}" style="height: 40px;"></div>
                        </div>
                    </div>
                </div>
            `;
        }
    </script>
</body>
</html>
"""

# Write HTML template to file
with open('templates/index.html', 'w') as f:
    f.write(html_template)

# Continue to Part 2...
# Part 2/3 - Data Fetching & Analysis Functions

def get_14d_history(symbol):
    """Get historical prices with fallback"""
    try:
        end = int(time.time())
        start = end - 60*60*24*14
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&period1={start}&period2={end}"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        chart = data['chart']['result'][0]
        return [{
            'date': datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d'),
            'close': close
        } for ts, close in zip(chart['timestamp'], chart['indicators']['quote'][0]['close']) if close]
    except Exception as e:
        logger.error(f"History error for {symbol}: {str(e)}")
        return []

def get_stock_info(symbol):
    """Get stock info with retry logic"""
    retries = 0
    max_retries = 3
    while retries < max_retries:
        try:
            time.sleep(random.uniform(0.5, 1.5))
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
            response = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }, timeout=15)
            data = response.json()
            
            if data['quoteResponse']['result']:
                quote = data['quoteResponse']['result'][0]
                return {
                    "symbol": symbol,
                    "name": quote.get('shortName', symbol),
                    "current_price": quote.get('regularMarketPrice'),
                    "sector": quote.get('sector', 'Unknown'),
                    "industry": quote.get('industry', 'Unknown'),
                    "market_cap": quote.get('marketCap'),
                    "pe_ratio": quote.get('trailingPE')
                }
            retries += 1
        except Exception as e:
            logger.error(f"Info error for {symbol}: {str(e)}")
            retries += 1
    return get_stock_info_by_scraping(symbol)

def get_historical_data(symbol, days=14):
    """Enhanced historical data with technical indicators"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?" \
              f"period1={int(start_date.timestamp())}&period2={int(end_date.timestamp())}&interval=1d"
        
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = response.json()
        
        # Process data and calculate indicators
        closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
        volumes = data['chart']['result'][0]['indicators']['quote'][0].get('volume', [])
        
        return {
            "symbol": symbol,
            "current_price": closes[-1] if closes else None,
            "technical_indicators": {
                "rsi": calculate_rsi(closes),
                "macd": calculate_macd(closes),
                "volume_analysis": analyze_volume(volumes)
            },
            "history_14d": get_14d_history(symbol)
        }
    except Exception as e:
        logger.error(f"Historical data error for {symbol}: {str(e)}")
        return calculate_fallback_data(symbol)

# Technical indicator calculations
def calculate_rsi(prices, periods=14):
    """Improved RSI calculation with error handling"""
    if len(prices) < periods + 1:
        return "N/A"
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-periods:])
    avg_loss = np.mean(losses[-periods:])
    
    if avg_loss == 0:
        return "Overbought (100)"
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    if rsi > 70: return f"Overbought ({rsi:.1f})"
    if rsi < 30: return f"Oversold ({rsi:.1f})"
    return f"Neutral ({rsi:.1f})"

# Continue to Part 3...
# Part 3/3 - Core Logic & Routes

def analyze_stock(symbol):
    """Enhanced analysis with sector data and news"""
    try:
        info = get_stock_info(symbol)
        history = get_historical_data(symbol)
        news = get_news_sentiment(symbol)
        
        # Generate recommendation
        recommendation = generate_recommendation(info, history)
        
        return {
            **info,
            **history,
            "news_sentiment": news,
            "recommendation": recommendation,
            "analysis_time": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {str(e)}")
        return create_fallback_entry(symbol)

def analyze_all_stocks():
    """Parallel analysis with performance tracking"""
    logger.info("Starting enhanced stock analysis...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(analyze_stock, symbol): symbol for symbol in STOCK_LIST}
        results = []
        
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                logger.error(f"Analysis error: {str(e)}")
                results.append(create_fallback_entry(futures[future]))

    logger.info(f"Analysis completed in {time.time() - start_time:.2f}s")
    return process_results(results)

@app.route('/')
def index():
    """Serve dashboard with enhanced features"""
    return render_template('index.html')

@app.route('/api/stocks')
def api_stocks():
    """Enhanced API endpoint with caching"""
    try:
        if os.path.exists('data/stock_analysis.json'):
            with open('data/stock_analysis.json', 'r') as f:
                cached_data = json.load(f)
                if (datetime.now() - datetime.fromisoformat(cached_data['timestamp'])) < timedelta(minutes=30):
                    return jsonify(cached_data)
        
        fresh_data = analyze_all_stocks()
        with open('data/stock_analysis.json', 'w') as f:
            json.dump(fresh_data, f)
        return jsonify(fresh_data)
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stream')
def stream():
    """SSE endpoint for real-time updates"""
    def event_stream():
        while True:
            data = analyze_all_stocks()
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(300)  # Update every 5 minutes
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == "__main__":
    if not os.path.exists('data/stock_analysis.json'):
        analyze_all_stocks()
    app.run(host='0.0.0.0', port=5000, threaded=True)