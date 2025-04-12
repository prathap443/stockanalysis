from flask import Flask, render_template, jsonify, send_from_directory
import requests
import json
import os
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

app = Flask(__name__)

# Create necessary directories
os.makedirs('templates', exist_ok=True)
os.makedirs('data', exist_ok=True)

# HTML template for dashboard
html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Market Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .stock-card { transition: transform 0.2s; }
        .stock-card:hover { transform: translateY(-5px); }
        .buy { background-color: #d1f8d1; }
        .sell { background-color: #ffd1d1; }
        .hold { background-color: #ffefd1; }
    </style>
</head>
<body>
    <div class="container my-4">
        <h1 class="mb-4">Stock Market Dashboard</h1>
        <p class="text-muted">Analysis of top stocks based on performance and technical indicators</p>
        <p id="lastUpdated" class="small text-muted">Last updated: Loading...</p>
        
        <button id="refreshBtn" class="btn btn-primary mb-4">Refresh Data</button>
        
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title text-success">Buy</h5>
                        <p id="buyCount" class="display-4">-</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title text-warning">Hold</h5>
                        <p id="holdCount" class="display-4">-</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title text-danger">Sell</h5>
                        <p id="sellCount" class="display-4">-</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="loading" class="text-center py-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading stock data...</p>
        </div>
        
        <div id="stocksList" class="row row-cols-1 row-cols-md-3 g-4" style="display: none;"></div>
        
        <div class="mt-5 text-center text-muted small">
            <p>Data for informational purposes only. Not financial advice.</p>
        </div>
    </div>
    
    <script>
        // Get elements
        const stocksList = document.getElementById('stocksList');
        const loading = document.getElementById('loading');
        const refreshBtn = document.getElementById('refreshBtn');
        const lastUpdated = document.getElementById('lastUpdated');
        const buyCount = document.getElementById('buyCount');
        const holdCount = document.getElementById('holdCount');
        const sellCount = document.getElementById('sellCount');
        
        // Load data on page load
        document.addEventListener('DOMContentLoaded', fetchStocks);
        
        // Refresh button
        refreshBtn.addEventListener('click', fetchStocks);
        
        function fetchStocks() {
            loading.style.display = 'block';
            stocksList.style.display = 'none';
            
            fetch('/api/stocks')
                .then(response => response.json())
                .then(data => {
                    displayStocks(data);
                })
                .catch(error => {
                    console.error('Error fetching stocks:', error);
                    loading.innerHTML = '<div class="alert alert-danger">Error loading data. Please try again.</div>';
                });
        }
        
        function displayStocks(data) {
            // Update counts
            buyCount.textContent = data.summary.BUY || 0;
            holdCount.textContent = data.summary.HOLD || 0;
            sellCount.textContent = data.summary.SELL || 0;
            lastUpdated.textContent = `Last updated: ${data.last_updated}`;
            
            // Clear existing stocks
            stocksList.innerHTML = '';
            
            // Add each stock
            data.stocks.forEach(stock => {
                const card = document.createElement('div');
                card.className = 'col';
                
                const changeClass = stock.percent_change_2w >= 0 ? 'text-success' : 'text-danger';
                const recClass = stock.recommendation === 'BUY' ? 'buy' : 
                                stock.recommendation === 'SELL' ? 'sell' : 'hold';
                
                card.innerHTML = `
                    <div class="card stock-card ${recClass}">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h5 class="card-title">${stock.symbol}</h5>
                                    <h6 class="card-subtitle mb-2 text-muted">${stock.name || ''}</h6>
                                </div>
                                <span class="badge bg-${stock.recommendation === 'BUY' ? 'success' : 
                                                    stock.recommendation === 'SELL' ? 'danger' : 'warning'}">
                                    ${stock.recommendation}
                                </span>
                            </div>
                            
                            <div class="d-flex justify-content-between mt-3">
                                <div>
                                    <h4>$${stock.current_price?.toFixed(2) || 'N/A'}</h4>
                                </div>
                                <div class="text-end">
                                    <h5 class="${changeClass}">
                                        ${stock.percent_change_2w >= 0 ? '+' : ''}${stock.percent_change_2w?.toFixed(2) || 0}%
                                    </h5>
                                    <small class="text-muted">2-week change</small>
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <small>${stock.reason || ''}</small>
                            </div>
                        </div>
                    </div>
                `;
                
                stocksList.appendChild(card);
            });
            
            // Hide loading, show stocks
            loading.style.display = 'none';
            stocksList.style.display = 'flex';
        }
    </script>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Write HTML template to file
with open('templates/index.html', 'w') as f:
    f.write(html)

# Default list of stocks to analyze if trending stocks can't be fetched
DEFAULT_STOCKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]

def get_trending_stocks():
    """Get trending stocks from Yahoo Finance or return default list"""
    try:
        url = "https://finance.yahoo.com/trending-tickers"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr", attrs={"class": "simpTblRow"})
            
            trending = []
            for row in rows[:10]:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    symbol = cols[0].text.strip()
                    trending.append(symbol)
            
            if trending:
                return trending[:10]
    except:
        pass
        
    print("Using default stock list")
    return DEFAULT_STOCKS

def get_stock_info(symbol):
    """Get basic stock info and current price"""
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get company name
        name_element = soup.find('h1')
        name = name_element.text if name_element else symbol
        
        # Get current price
        price_element = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
        price = float(price_element['value']) if price_element and 'value' in price_element.attrs else None
        
        return {
            "symbol": symbol,
            "name": name,
            "current_price": price
        }
    except Exception as e:
        print(f"Error getting info for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "name": symbol,
            "current_price": None
        }

def get_historical_data(symbol, days=14):
    """Get historical price data for analysis"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for Yahoo Finance API
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        # Using Yahoo Finance API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start_timestamp}&period2={end_timestamp}&interval=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            return {"error": f"No data returned for {symbol}"}
        
        result = data["chart"]["result"][0]
        
        # Extract timestamps and price data
        timestamps = result["timestamp"]
        close_prices = result["indicators"]["quote"][0]["close"]
        
        # Remove None values
        valid_data = [(t, c) for t, c in zip(timestamps, close_prices) if c is not None]
        
        if not valid_data:
            return {"error": f"No valid price data for {symbol}"}
        
        timestamps, close_prices = zip(*valid_data)
        
        # Calculate key metrics
        start_price = close_prices[0]
        end_price = close_prices[-1]
        
        # Calculate performance metrics
        price_change = end_price - start_price
        percent_change = (price_change / start_price) * 100
        
        return {
            "symbol": symbol,
            "start_price": start_price,
            "end_price": end_price,
            "current_price": end_price,
            "percent_change_2w": percent_change
        }
    except Exception as e:
        print(f"Error getting history for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "error": str(e),
            "percent_change_2w": 0,
            "current_price": None
        }

def analyze_stock(symbol):
    """Analyze a stock and generate recommendation"""
    # Get basic info
    info = get_stock_info(symbol)
    
    # Get historical data
    history = get_historical_data(symbol)
    
    if "error" in history:
        return {
            "symbol": symbol,
            "name": info.get("name", symbol),
            "recommendation": "UNKNOWN",
            "reason": f"Error: {history.get('error', 'Unknown error')}",
            "current_price": info.get("current_price"),
            "percent_change_2w": 0
        }
    
    # Extract key metrics
    percent_change = history["percent_change_2w"]
    current_price = history["current_price"] or info.get("current_price")
    
    # Simple recommendation logic based on 2-week performance
    recommendation = "HOLD"
    reason = ""
    
    if percent_change > 7:
        recommendation = "SELL"
        reason = f"Strong upward momentum (+{percent_change:.2f}% in 2 weeks) suggests potential profit-taking opportunity."
    elif percent_change > 3:
        recommendation = "HOLD"
        reason = f"Good performance (+{percent_change:.2f}% in 2 weeks) but not extreme enough to change position."
    elif percent_change < -7:
        recommendation = "BUY"
        reason = f"Significant drop ({percent_change:.2f}% in 2 weeks) may represent a buying opportunity if fundamentals remain strong."
    elif percent_change < -3:
        recommendation = "HOLD"
        reason = f"Stock is down ({percent_change:.2f}% in 2 weeks) but not enough to strongly change position."
    else:
        recommendation = "HOLD"
        reason = f"Stable price action ({percent_change:.2f}% in 2 weeks) suggests maintaining current position."
    
    return {
        "symbol": symbol,
        "name": info.get("name", symbol),
        "recommendation": recommendation,
        "percent_change_2w": percent_change,
        "current_price": current_price,
        "reason": reason
    }

def analyze_all_stocks():
    """Analyze all trending stocks"""
    print("Starting stock analysis...")
    trending_symbols = get_trending_stocks()
    
    results = []
    recommendations = {"BUY": 0, "HOLD": 0, "SELL": 0, "UNKNOWN": 0}
    
    for symbol in trending_symbols:
        try:
            print(f"Analyzing {symbol}...")
            analysis = analyze_stock(symbol)
            recommendations[analysis.get("recommendation", "UNKNOWN")] += 1
            results.append(analysis)
            # Small delay to avoid rate limiting
            time.sleep(1)
        except Exception as e:
            print(f"Error analyzing {symbol}: {str(e)}")
            results.append({
                "symbol": symbol,
                "recommendation": "UNKNOWN",
                "error": str(e)
            })
    
    # Save data to file with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "stocks": results,
        "summary": recommendations,
        "last_updated": timestamp
    }
    
    with open('data/stock_analysis.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Analysis complete. Analyzed {len(results)} stocks.")
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stocks')
def api_stocks():
    try:
        # Try to read from cached file first
        try:
            with open('data/stock_analysis.json', 'r') as f:
                data = json.load(f)
                # Check if data is recent (less than 30 minutes old)
                last_updated = datetime.strptime(data['last_updated'], "%Y-%m-%d %H:%M:%S")
                age = datetime.now() - last_updated
                
                if age.total_seconds() < 1800:  # 30 minutes
                    return jsonify(data)
        except:
            pass
        
        # No recent data, run analysis
        return jsonify(analyze_all_stocks())
    except Exception as e:
        print(f"API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    try:
        data = analyze_all_stocks()
        return jsonify({"success": True, "message": "Data refreshed", "data": data})
    except Exception as e:
        print(f"Refresh error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    # Initial data load if no existing data
    if not os.path.exists('data/stock_analysis.json'):
        try:
            analyze_all_stocks()
        except Exception as e:
            print(f"Initial analysis error: {str(e)}")
    
    # Start the web server
    print("Starting web server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)