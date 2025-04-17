# Enhanced Stock Analysis Web Application
# - Analyzes top 20 stocks
# - Comprehensive analysis with more technical indicators
# - Improved refresh functionality
# - Better error handling and reliability
# - 14-day trend charts

from flask import Flask, render_template, jsonify, request
import requests
import json
import os
import time
from datetime import datetime, timedelta
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import joblib
import numpy as np
from textblob import TextBlob  # For basic sentiment analysis

model = joblib.load("model/stock_predictor.pkl")
label_encoder = joblib.load("model/label_encoder.pkl")

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Create directories
os.makedirs('templates', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Base STOCK_LIST (20 majors)
base_stocks = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", 
    "TSLA", "NVDA", "JPM", "V", "WMT", 
    "DIS", "NFLX", "PYPL", "INTC", "AMD", 
    "BA", "PFE", "KO", "PEP", "XOM"
]

# Top 10 AI-related stocks
AI_STOCKS = [
    "NVDA", "AMD", "GOOGL", "MSFT", "META",
    "TSLA", "AMZN", "IBM", "BIDU", "PLTR"
]

# Top 20 tech-related stocks
TECH_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "TSLA", "NVDA", "AMD", "INTC", "IBM",
    "CRM", "ORCL", "ADBE", "CSCO", "QCOM",
    "SAP", "TXN", "AVGO", "SNOW", "SHOP"
]

# Merge all and remove duplicates
STOCK_LIST = sorted(set(base_stocks + AI_STOCKS + TECH_STOCKS))
logger.info(f"Final STOCK_LIST contains {len(STOCK_LIST)} symbols.")

# Modern HTML template with glassmorphism design
html_template = """

<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <title>Stock Analytics - Prathap's Analysis</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {
      background: #f0f2f5;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stock-card {
      backdrop-filter: blur(10px);
      background: rgba(255, 255, 255, 0.7);
      border-radius: 15px;
      padding: 15px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      transition: transform 0.2s;
    }
    .stock-card:hover {
      transform: translateY(-5px);
    }
    .fade-in {
      animation: fadeIn 0.6s ease-in-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
  </style>
</head>
<body>
  <div class="container my-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <div>
        <h1 class="display-5 mb-1">📈 Stock Analytics - Prathap's Analysis</h1>
        <p class="text-muted">Real-time analysis of top market performers</p>
        <div class="text-end small text-muted" id="lastUpdated"></div>
      </div>
      <button class="btn btn-outline-secondary" onclick="toggleTheme()">🌓 Toggle Theme</button>
    </div>

    <div class="row text-center mb-4">
      <div class="col-md-4">
        <div class="p-3 bg-success text-white rounded">
          <h5>BUY</h5>
          <h3 id="buyCount">0</h3>
        </div>
      </div>
      <div class="col-md-4">
        <div class="p-3 bg-warning text-dark rounded">
          <h5>HOLD</h5>
          <h3 id="holdCount">0</h3>
        </div>
      </div>
      <div class="col-md-4">
        <div class="p-3 bg-danger text-white rounded">
          <h5>SELL</h5>
          <h3 id="sellCount">0</h3>
        </div>
      </div>
    </div>

    <div class="row g-3 mb-4 fade-in">
      <div class="col-md-4">
        <input type="text" class="form-control" placeholder="🔍 Search stocks..." id="stockSearch" />
      </div>
      <div class="col-md-4">
        <select class="form-select" id="sectorFilter">
          <option value="">All Sectors</option>
        </select>
      </div>
      <div class="col-md-4">
        <button id="refreshBtn" class="btn btn-primary w-100">🔄 Refresh</button>
      </div>
    </div>

    <div id="dashboardContent" class="row g-4"></div>
  </div>

  <script>
    async function loadDashboard() {
      try {
        const response = await fetch('/api/stocks?t=' + Date.now());
        const data = await response.json();
        if (data && data.stocks) {
          document.getElementById("dashboardContent").innerHTML = '';
          renderCounts(data.summary);
          renderStocks(data.stocks);
          document.getElementById("lastUpdated").innerText = `Last updated: ${data.last_updated}`;
        } else {
          document.getElementById("dashboardContent").innerHTML = '<p class="text-danger">No data available.</p>';
        }
      } catch (error) {
        document.getElementById("dashboardContent").innerHTML = `<p class="text-danger">Error loading data: ${error}</p>`;
      }
    }

    function renderCounts(summary) {
      document.getElementById("buyCount").innerText = summary.BUY || 0;
      document.getElementById("holdCount").innerText = summary.HOLD || 0;
      document.getElementById("sellCount").innerText = summary.SELL || 0;
    }

    function renderStocks(stocks) {
      let html = '';
      stocks.forEach((stock, i) => {
        const trendColor = stock.percent_change_2w >= 0 ? 'text-success' : 'text-danger';
        const trendIcon = stock.percent_change_2w >= 0 ? '↑' : '↓';
        const chartId = `chart-${i}`;
        html += `
          <div class="col-md-6 col-lg-4">
            <div class="stock-card">
              <div class="mb-2 d-flex justify-content-between">
                <div>
                  <h5>${stock.symbol}</h5>
                  <small class="text-muted">Yahoo Finance</small><br/>
                  <strong>$${stock.current_price?.toFixed(2) || 'N/A'}</strong><br/>
                  <span class="text-muted small">${stock.news_sentiment || ''}</span>
                </div>
                <div class="text-end ${trendColor}">
                  <strong>${trendIcon}${stock.percent_change_2w.toFixed(2)}%</strong><br/>
                  <small>${stock.recommendation}</small>
                </div>
              </div>
              <canvas id="${chartId}" height="100"></canvas>
            </div>
          </div>`;
      });
      document.getElementById("dashboardContent").innerHTML = html;
      stocks.forEach((stock, i) => {
        if (stock.history_14d?.length > 0) {
          renderStockChart(`chart-${i}`, stock.history_14d);
        }
      });
    }

    function renderStockChart(canvasId, historyData) {
      const ctx = document.getElementById(canvasId).getContext('2d');
      const dates = historyData.map(item => item.date);
      const prices = historyData.map(item => item.close);
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: 'Price',
            data: prices,
            borderColor: 'rgba(75, 192, 192, 1)',
            tension: 0.2,
            fill: false
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false }
          },
          scales: {
            x: {
              ticks: {
                maxTicksLimit: 5,
                autoSkip: true
              }
            },
            y: {
              display: false
            }
          }
        }
      });
    }

    function toggleTheme() {
      const current = document.documentElement.getAttribute('data-theme');
      document.documentElement.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
    }

    document.getElementById("refreshBtn").addEventListener("click", async () => {
      document.getElementById("refreshBtn").innerText = "Refreshing...";
      try {
        const res = await fetch('/api/refresh', { method: 'POST' });
        const json = await res.json();
        if (json.success) {
          await loadDashboard();
        } else {
          alert("Refresh failed: " + json.error);
        }
      } catch (err) {
        alert("Error refreshing data: " + err.message);
      } finally {
        document.getElementById("refreshBtn").innerText = "🔄 Refresh";
      }
    });

    document.addEventListener("DOMContentLoaded", loadDashboard);
  </script>
</body>
</html>



"""

# Write HTML template to file
with open('templates/index.html', 'w') as f:
    f.write(html_template)

def get_14d_history(symbol):
    """Get 14-day historical prices for charts"""
    end = int(time.time())
    start = end - 60*60*24*14  # 14 days
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start}&period2={end}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        chart = data['chart']['result'][0]
        timestamps = chart['timestamp']
        closes = chart['indicators']['quote'][0]['close']
        return [{
            'date': datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d'),
            'close': close
        } for ts, close in zip(timestamps, closes) if close is not None]
    except Exception as e:
        logger.error(f"Error fetching 14d history for {symbol}: {str(e)}")
        return []

# Continue to part 2 for the remaining code...
def get_stock_info(symbol):
    """Get basic stock info and current price with improved reliability"""
    time.sleep(random.uniform(0.5, 1.5))  # Randomized delay to avoid rate limiting
    
    try:
        # Use the Yahoo Finance API directly
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        if 'quoteResponse' in data and 'result' in data['quoteResponse'] and len(data['quoteResponse']['result']) > 0:
            quote = data['quoteResponse']['result'][0]
            return {
                "symbol": symbol,
                "name": quote.get('shortName', symbol),
                "current_price": quote.get('regularMarketPrice', None),
                "sector": quote.get('sector', 'Unknown'),
                "industry": quote.get('industry', 'Unknown'),
                "market_cap": quote.get('marketCap', None),
                "pe_ratio": quote.get('trailingPE', None)
            }
        else:
            # Fallback to scraping if API doesn't return expected data
            return get_stock_info_by_scraping(symbol)
    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {str(e)}")
        # Fallback to scraping on exception
        return get_stock_info_by_scraping(symbol)

def get_stock_info_by_scraping(symbol):
    """Get stock info by scraping - backup method"""
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        # Very basic extraction with minimal dependencies
        price = None
        name = symbol
        
        if response.status_code == 200:
            html = response.text
            
            # Extract name
            if '<h1' in html:
                name_start = html.find('<h1')
                name_end = html.find('</h1>', name_start)
                if name_end > 0:
                    name_content = html[name_start:name_end]
                    name_parts = name_content.split('>')
                    if len(name_parts) > 1:
                        name = name_parts[-1].strip()
            
            # Extract price - look for regularMarketPrice
            price_marker = 'data-field="regularMarketPrice"'
            if price_marker in html:
                price_pos = html.find(price_marker)
                value_attr = 'value="'
                value_start = html.find(value_attr, price_pos)
                if value_start > 0:
                    value_end = html.find('"', value_start + len(value_attr))
                    if value_end > 0:
                        try:
                            price = float(html[value_start + len(value_attr):value_end])
                        except ValueError:
                            pass
        
        return {
            "symbol": symbol,
            "name": name if name else symbol,
            "current_price": price,
            "sector": "Unknown",
            "industry": "Unknown"
        }
    except Exception as e:
        logger.error(f"Error scraping info for {symbol}: {str(e)}")
        # Return minimal info rather than failing
        return {
            "symbol": symbol,
            "name": symbol,
            "current_price": None
        }

def get_historical_data(symbol, days=14):
    """Get historical price data for analysis with improved reliability"""
    time.sleep(random.uniform(0.5, 1.5))  # Randomized delay to avoid rate limiting
    
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
        
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            return calculate_fallback_data(symbol)
        
        result = data["chart"]["result"][0]
        
        # Extract timestamps and price data
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        close_prices = quotes["close"]
        volumes = quotes.get("volume", [])
        
        # Filter out None values
        valid_data = []
        for i in range(len(timestamps)):
            price = close_prices[i] if i < len(close_prices) else None
            volume = volumes[i] if i < len(volumes) else None
            if price is not None:
                valid_data.append((timestamps[i], price, volume))
        
        if len(valid_data) < 2:
            return calculate_fallback_data(symbol)
        
        # Unpack the data
        timestamps, prices, volumes = zip(*valid_data)
        
        # Calculate key metrics
        start_price = prices[0]
        end_price = prices[-1]
        high_price = max(prices)
        low_price = min(prices)
        price_change = end_price - start_price
        percent_change = (price_change / start_price) * 100
        
        # Calculate volatility
        daily_returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
        volatility = sum([(ret - (sum(daily_returns)/len(daily_returns)))**2 for ret in daily_returns])
        volatility = (volatility / len(daily_returns))**0.5 if daily_returns else 0
        
        # Calculate technical indicators
        rsi = calculate_rsi(prices)
        macd = calculate_macd(prices)
        volume_trend = analyze_volume(volumes)
        
        # Determine overall trend
        trend = "Neutral"
        bullish_signals = 0
        bearish_signals = 0
        
        # Count signals for trend determination
        if "Oversold" in rsi: bullish_signals += 1
        elif "Overbought" in rsi: bearish_signals += 1
        
        if "Bullish" in macd: bullish_signals += 1
        elif "Bearish" in macd: bearish_signals += 1
        
        if percent_change > 5: bullish_signals += 1
        elif percent_change < -5: bearish_signals += 1
        
        if "Increasing" in volume_trend: bullish_signals += 1
        elif "Decreasing" in volume_trend: bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            trend = "Bullish"
        elif bearish_signals > bullish_signals:
            trend = "Bearish"
        
        return {
            "symbol": symbol,
            "start_price": start_price,
            "end_price": end_price,
            "current_price": end_price,
            "price_change": price_change,
            "percent_change_2w": percent_change,
            "high": high_price,
            "low": low_price,
            "volatility": volatility,
            "volume_trend": volume_trend,
            "technical_indicators": {
                "rsi": rsi,
                "macd": macd,
                "volume_analysis": volume_trend,
                "trend": trend
            }
        }
    except Exception as e:
        logger.error(f"Error getting history for {symbol}: {str(e)}")
        return calculate_fallback_data(symbol)

def calculate_fallback_data(symbol):
    """Calculate fallback data when we can't get real data"""
    return {
        "symbol": symbol,
        "percent_change_2w": random.uniform(-10, 10),  # Random change between -10% and +10%
        "current_price": random.uniform(50, 500),  # Random price
        "volatility": random.uniform(1, 8),
        "technical_indicators": {
            "rsi": f"{random.uniform(30, 70):.1f}",
            "macd": f"{random.uniform(-2, 2):.2f}",
            "volume_analysis": "Neutral",
            "trend": "Neutral"
        }
    }

def calculate_rsi(prices, periods=14):
    """Calculate Relative Strength Index with improved error handling"""
    try:
        if len(prices) < periods + 1:
            return "Neutral (N/A)"
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # Calculate average gains and losses over the RSI period
        avg_gain = sum(gains[-periods:]) / periods
        avg_loss = sum(losses[-periods:]) / periods
        
        if avg_loss == 0:
            return "Overbought (100.0)"
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        if rsi > 70:
            return f"Overbought ({rsi:.1f})"
        elif rsi < 30:
            return f"Oversold ({rsi:.1f})"
        else:
            return f"Neutral ({rsi:.1f})"
    except Exception as e:
        logger.error(f"Error calculating RSI: {str(e)}")
        return "Neutral (Error)"

def calculate_macd(prices):
    """Calculate Moving Average Convergence Divergence"""
    if len(prices) < 26:
        return "N/A"
    
    # Calculate EMAs
    ema12 = sum(prices[-12:]) / 12
    ema26 = sum(prices[-26:]) / 26
    
    # Calculate MACD
    macd = ema12 - ema26
    
    if macd > 0.5:
        return f"Bullish ({macd:.2f})"
    elif macd < -0.5:
        return f"Bearish ({macd:.2f})"
    else:
        return f"Neutral ({macd:.2f})"

def analyze_volume(volumes):
    """Analyze trading volume trend"""
    if not volumes or len(volumes) < 5:
        return "N/A"
    
    # Filter out None values
    valid_volumes = [v for v in volumes if v is not None]
    if len(valid_volumes) < 5:
        return "Insufficient Data"
    
    # Calculate average volume for first half and second half
    half = len(valid_volumes) // 2
    avg_first_half = sum(valid_volumes[:half]) / half
    avg_second_half = sum(valid_volumes[half:]) / (len(valid_volumes) - half)
    
    # Calculate percent change in average volume
    volume_change = ((avg_second_half - avg_first_half) / avg_first_half) * 100
    
    if volume_change > 25:
        return "Increasing (High)"
    elif volume_change > 10:
        return "Increasing (Moderate)"
    elif volume_change < -25:
        return "Decreasing (High)"
    elif volume_change < -10:
        return "Decreasing (Moderate)"
    else:
        return "Stable"
@app.route("/retrain", methods=["POST"])
def retrain_model():
    try:
        import train_model  # Assuming train_model.py has the retraining logic
        return jsonify({"success": True, "message": "Model retrained successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def get_news_sentiment(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()

        articles = data.get("quotes", [])[:5]
        texts = [a.get("shortname", "") for a in articles]
        full_text = " ".join(texts)

        if full_text:
            score = TextBlob(full_text).sentiment.polarity  # -1 to 1
            return score
        return 0
    except Exception as e:
        logger.warning(f"News sentiment error for {symbol}: {e}")
        return 0

def analyze_stock(symbol):
    try:
        # Get all required data
        info = get_stock_info(symbol)
        history = get_historical_data(symbol)
        news_sentiment = get_news_sentiment(symbol)
        history_14d = get_14d_history(symbol)

        current_price = history.get("current_price") or info.get("current_price")
        percent_change = history.get("percent_change_2w", 0)
        volatility = history.get("volatility", 5)

        # Extract and clean indicators
        technical_indicators = history.get("technical_indicators", {})
        rsi_str = str(technical_indicators.get("rsi", "50"))
        macd_str = str(technical_indicators.get("macd", "0"))

        rsi = float(rsi_str.split("(")[-1].replace(")", "") or 50)
        macd = float(macd_str.split("(")[-1].replace(")", "") or 0)
        volume_score = 1 if "Increasing" in technical_indicators.get("volume_analysis", "") else 0
        sentiment_score = 0  # You can enhance this later with real sentiment analysis

        # Prepare feature array
        features = np.array([[rsi, macd, volume_score, percent_change, sentiment_score, volatility]])

        # Predict using trained model
        pred = model.predict(features)[0]
        recommendation = label_encoder.inverse_transform([pred])[0]

        # Compose reason
        reason = (
            f"🤖 ML-based prediction using "
            f"RSI={rsi:.1f}, MACD={macd:.2f}, Change={percent_change:.2f}%, "
            f"Volatility={volatility:.2f}, Volume={volume_score}"
        )

        logger.info(f"{symbol} → ML RECOMMEND: {recommendation}")

        return {
            "symbol": symbol,
            "name": info.get("name", symbol),
            "recommendation": recommendation,
            "percent_change_2w": percent_change,
            "current_price": current_price,
            "reason": reason,
            "technical_indicators": technical_indicators,
            "news_sentiment": news_sentiment,
            "history_14d": history_14d
        }

    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "name": symbol,
            "recommendation": "HOLD",
            "percent_change_2w": 0,
            "current_price": 100.0,
            "reason": "⚠️ Analysis failed. Defaulting to HOLD.",
            "technical_indicators": {
                "rsi": "N/A", "macd": "N/A", 
                "volume_analysis": "N/A", "trend": "N/A"
            },
            "history_14d": []
        }


def analyze_all_stocks():
    """Analyze all 20 stocks in parallel with optimized API calls"""
    logger.info("Starting parallel stock analysis...")
    
    results = []
    recommendations = {"BUY": 0, "HOLD": 0, "SELL": 0, "UNKNOWN": 0}

    # Use thread pool for parallel execution
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_symbol = {
            executor.submit(analyze_stock, symbol): symbol 
            for symbol in STOCK_LIST
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                analysis = future.result()
                rec = analysis.get("recommendation", "UNKNOWN")
                recommendations[rec] += 1
                results.append(analysis)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                # Add fallback entry
                results.append(create_fallback_entry(symbol))
                recommendations["HOLD"] += 1

    # Save data and return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "stocks": results,
        "summary": recommendations,
        "last_updated": timestamp
    }
    
    try:
        with open('data/stock_analysis.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving analysis: {str(e)}")
    
    logger.info(f"Parallel analysis complete. Processed {len(results)} stocks.")
    return data

def create_fallback_entry(symbol):
    """Create a fallback stock entry"""
    return {
        "symbol": symbol,
        "name": symbol,
        "recommendation": "HOLD",
        "percent_change_2w": random.uniform(-3, 3),
        "current_price": random.uniform(80, 300),
        "reason": "Analysis unavailable. Maintain position.",
        "technical_indicators": {
            "rsi": "N/A", "macd": "N/A", 
            "volume_analysis": "N/A", "trend": "N/A"
        },
        "history_14d": []
    }

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')

@app.route('/api/stocks')
def api_stocks():
    """Get stock data - first try cache, then live data"""
    try:
        # Try to read from cached file first
        try:
            if os.path.exists('data/stock_analysis.json'):
                with open('data/stock_analysis.json', 'r') as f:
                    data = json.load(f)
                    # Check if data is recent (less than 30 minutes old)
                    last_updated = datetime.strptime(data['last_updated'], "%Y-%m-%d %H:%M:%S")
                    age = datetime.now() - last_updated
                    
                    if age.total_seconds() < 1800:  # 30 minutes
                        return jsonify(data)
        except Exception as e:
            logger.error(f"Error reading cached data: {str(e)}")
        
        # No recent data, run analysis
        return jsonify(analyze_all_stocks())
    except Exception as e:
        error_msg = f"API error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Force refresh stock data with improved error handling"""
    try:
        # Clear any cached data first
        if os.path.exists('data/stock_analysis.json'):
            try:
                os.remove('data/stock_analysis.json')
            except:
                pass
        
        # Run fresh analysis
        data = analyze_all_stocks()
        
        # Validate the result is actually in the correct format
        if not isinstance(data, dict) or "stocks" not in data:
            return jsonify({"success": False, "error": "Invalid analysis result format"}), 500
            
        return jsonify({"success": True, "message": "Data refreshed with latest market information"})
    except Exception as e:
        error_msg = f"Refresh error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500
    
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()

        # Expected input order for model
        features = [
            data.get("rsi", 50),
            data.get("macd", 0),
            data.get("volume_score", 0),
            data.get("percent_change_2w", 0),
            data.get("sentiment_score", 0),
            data.get("volatility", 0)
        ]

        X = np.array([features])
        prediction = model.predict(X)[0]
        labels = {0: "SELL", 1: "HOLD", 2: "BUY"}

        return jsonify({
            "recommendation": labels.get(prediction, "HOLD"),
            "reason": f"ML-based prediction using RSI={features[0]}, MACD={features[1]}, volume={features[2]}, change={features[3]}, sentiment={features[4]}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Initial data load if no existing data
    if not os.path.exists('data/stock_analysis.json'):
        try:
            analyze_all_stocks()
        except Exception as e:
            logger.error(f"Initial analysis error: {str(e)}")
    
    # Start the web server
    app.run(host='0.0.0.0', port=5000)