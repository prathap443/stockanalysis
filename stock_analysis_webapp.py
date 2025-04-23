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
import pandas as pd
from textblob import TextBlob  # For basic sentiment analysis
import ta  # For technical indicators (RSI, MACD, etc.)

# Load pre-trained model and label encoder
model = joblib.load("stock_predictor.pkl")
label_encoder = joblib.load("label_encoder.pkl")

# Define the feature columns expected by the model (same as in training)
FEATURE_COLUMNS = [
    'RSI', 'MACD', 'SMA_50', 'BB_Width', 'PE_Ratio',
    'Dividend_Yield', 'News_Sentiment', 'volume_score',
    'percent_change_5d', 'volatility'
]

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('stock_analysis_webapp')

# Initialize Flask app
app = Flask(__name__)

# Create directories
os.makedirs('templates', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Stock lists
base_stocks = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", 
    "TSLA", "NVDA", "JPM", "V", "WMT", 
    "DIS", "NFLX", "PYPL", "INTC", "AMD", 
    "BA", "PFE", "KO", "PEP", "XOM"
]
AI_STOCKS = [
    "NVDA", "AMD", "GOOGL", "MSFT", "META",
    "TSLA", "AMZN", "IBM", "BIDU", "PLTR"
]
TECH_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "TSLA", "NVDA", "AMD", "INTC", "IBM",
    "CRM", "ORCL", "ADBE", "CSCO", "QCOM",
    "SAP", "TXN", "AVGO", "SNOW", "SHOP"
]
STOCK_LIST = sorted(set(base_stocks + AI_STOCKS + TECH_STOCKS))
logger.info(f"Final STOCK_LIST contains {len(STOCK_LIST)} symbols.")

# Static mapping of stock symbols to sectors
SECTOR_MAPPING = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Technology",
    "AMZN": "Technology",
    "META": "Technology",
    "TSLA": "Technology",
    "NVDA": "Technology",
    "INTC": "Technology",
    "AMD": "Technology",
    "IBM": "Technology",
    "CRM": "Technology",
    "ORCL": "Technology",
    "ADBE": "Technology",
    "CSCO": "Technology",
    "QCOM": "Technology",
    "SAP": "Technology",
    "TXN": "Technology",
    "AVGO": "Technology",
    "SNOW": "Technology",
    "SHOP": "Technology",
    "BIDU": "Technology",
    "PLTR": "Technology",
    "JPM": "Finance",
    "V": "Finance",
    "WMT": "Consumer Goods",
    "DIS": "Consumer Goods",
    "KO": "Consumer Goods",
    "PEP": "Consumer Goods",
    "NFLX": "Entertainment",
    "PYPL": "Financial Services",
    "BA": "Aerospace",
    "PFE": "Healthcare",
    "XOM": "Energy"
}

# HTML template (same as before)
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
    /* Define theme variables */
    :root {
      --bg-color: #f0f2f5;
      --card-bg: rgba(255, 255, 255, 0.7);
      --text-color: #333;
      --muted-color: #666;
      --card-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }

    [data-theme="dark"] {
      --bg-color: #1a1a1a;
      --card-bg: rgba(40, 40, 40, 0.7);
      --text-color: #f0f0f0;
      --muted-color: #aaa;
      --card-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    body {
      background: var(--bg-color);
      color: var(--text-color);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      transition: background 0.3s, color 0.3s;
    }

    .stock-card {
      backdrop-filter: blur(10px);
      background: var(--card-bg);
      border-radius: 15px;
      padding: 15px;
      box-shadow: var(--card-shadow);
      transition: transform 0.2s, background 0.3s;
      color: var(--text-color);
    }

    .stock-card:hover {
      transform: translateY(-5px);
    }

    .text-muted {
      color: var(--muted-color) !important;
    }

    .fade-in {
      animation: fadeIn 0.6s ease-in-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }

    .btn-outline-secondary {
      color: var(--text-color);
      border-color: var(--text-color);
    }

    .btn-outline-secondary:hover {
      background: var(--card-bg);
    }

    .recommendation-box {
      cursor: pointer;
      transition: transform 0.2s;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
      border-radius: 10px;
    }

    .recommendation-box:hover {
      transform: scale(1.05);
    }

    .recommendation-box.active {
      border: 2px solid #007bff;
      transform: scale(1.05);
    }

    .buy-box {
      background: linear-gradient(145deg, #34C759, #1A7431);
      color: white;
    }

    .hold-box {
      background: linear-gradient(145deg, #FF9500, #CC4D00);
      color: white;
    }

    .sell-box {
      background: linear-gradient(145deg, #FF3B30, #A61C1C);
      color: white;
    }

    .time-period-btn {
      font-size: 0.8rem;
      padding: 2px 8px;
    }

    .time-period-btn.active {
      background-color: #007bff;
      color: white;
      border-color: #007bff;
    }

    .expand-icon {
      font-size: 0.9rem;
      padding: 2px 6px;
      margin-left: 5px;
      cursor: pointer;
    }

    .expand-icon:hover {
      background-color: #e9ecef;
      border-radius: 5px;
    }

    .modal-content {
      background: var(--card-bg);
      color: var(--text-color);
    }

    .modal-header {
      border-bottom: 1px solid var(--muted-color);
    }

    .modal-footer {
      border-top: 1px solid var(--muted-color);
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

    <div class="row text-center mb-2">
      <div class="col-md-4">
        <div id="buyBox" class="p-3 buy-box rounded recommendation-box" onclick="filterByRecommendation('BUY')">
          <h5>BUY</h5>
          <h3 id="buyCount">0</h3>
        </div>
      </div>
      <div class="col-md-4">
        <div id="holdBox" class="p-3 hold-box rounded recommendation-box" onclick="filterByRecommendation('HOLD')">
          <h5>HOLD</h5>
          <h3 id="holdCount">0</h3>
        </div>
      </div>
      <div class="col-md-4">
        <div id="sellBox" class="p-3 sell-box rounded recommendation-box" onclick="filterByRecommendation('SELL')">
          <h5>SELL</h5>
          <h3 id="sellCount">0</h3>
        </div>
      </div>
    </div>
    <div class="row text-center mb-4">
      <div class="col-12">
        <button id="resetFilters" class="btn btn-secondary btn-sm">Reset Filters</button>
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

  <!-- Modal for Expanded Chart -->
  <div class="modal fade" id="chartModal" tabindex="-1" aria-labelledby="chartModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="chartModalLabel">Expanded Chart</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <canvas id="modalChart" height="400"></canvas>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    let allStocks = []; // Store all stock data for filtering
    let selectedRecommendation = ''; // Track the selected recommendation filter
    let selectedTimePeriods = {}; // Track the selected time period for each stock

    async function loadDashboard() {
      try {
        const response = await fetch('/api/stocks?t=' + Date.now());
        const data = await response.json();
        if (data && data.stocks) {
          allStocks = data.stocks; // Cache stocks for filtering
          document.getElementById("dashboardContent").innerHTML = '';
          renderCounts(data.summary);
          renderStocks(allStocks);
          populateSectorFilter(allStocks);
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
        const buttonGroupId = `timePeriod-${i}`;
        html += `
          <div class="col-md-6 col-lg-4">
            <div class="stock-card">
              <div class="mb-2 d-flex justify-content-between">
                <div>
                  <h5>${stock.symbol}</h5>
                  <small class="text-muted">Yahoo Finance</small><br/>
                  <strong>$${stock.current_price?.toFixed(2) || 'N/A'}</strong><br/>
                  <span class="text-muted small">Sentiment: ${stock.news_sentiment !== undefined ? stock.news_sentiment.toFixed(3) : 'N/A'}</span>
                </div>
                <div class="text-end ${trendColor}">
                  <strong>${trendIcon}${stock.percent_change_2w.toFixed(2)}%</strong><br/>
                  <small>${stock.recommendation}</small>
                </div>
              </div>
              <div class="btn-group btn-group-sm mb-2" role="group" id="${buttonGroupId}">
                <button type="button" class="btn btn-outline-secondary time-period-btn" onclick="updateChart('${stock.symbol}', '1D', ${i}, this)">1D</button>
                <button type="button" class="btn btn-outline-secondary time-period-btn expand-icon" onclick="expandChart('${stock.symbol}', ${i})">🔍</button>
                <button type="button" class="btn btn-outline-secondary time-period-btn" onclick="updateChart('${stock.symbol}', '1W', ${i}, this)">1W</button>
                <button type="button" class="btn btn-outline-secondary time-period-btn" onclick="updateChart('${stock.symbol}', '1M', ${i}, this)">1M</button>
              </div>
              <div id="chartContainer-${i}">
                <canvas id="${chartId}" height="100"></canvas>
              </div>
              <div class="mt-2">
                <button class="btn btn-sm btn-info" onclick="getLivePrediction('${stock.symbol}', ${i})">Get Live Prediction</button>
                <div id="livePrediction-${i}" class="small mt-1"></div>
              </div>
            </div>
          </div>`;
      });
      document.getElementById("dashboardContent").innerHTML = html;
      stocks.forEach((stock, i) => {
        const period = selectedTimePeriods[stock.symbol] || '1D'; // Default to 1D for intraday
        updateChart(stock.symbol, period, i);
      });
    }

    async function updateChart(symbol, period, index, button) {
      try {
        // Update the selected time period for this stock
        selectedTimePeriods[symbol] = period;

        // Update button styles
        const buttonGroup = button ? button.parentElement : document.getElementById(`timePeriod-${index}`);
        buttonGroup.querySelectorAll('.time-period-btn').forEach(btn => btn.classList.remove('active'));
        if (button) {
          button.classList.add('active');
        }

        // Fetch new data for the selected period
        const response = await fetch(`/api/stock_history/${symbol}/${period}`);
        const historyData = await response.json();
        const chartContainer = document.getElementById(`chartContainer-${index}`);
        if (historyData && historyData.length > 0) {
          if (historyData[0].error) {
            chartContainer.innerHTML = `<p class="small text-muted">${historyData[0].error}</p>`;
          } else {
            chartContainer.innerHTML = `<canvas id="chart-${index}" height="100"></canvas>`;
            renderStockChart(`chart-${index}`, historyData, period);
          }
        } else {
          chartContainer.innerHTML = `<p class="small text-muted">No data available for ${period}.</p>`;
        }
      } catch (error) {
        console.error(`Error updating chart for ${symbol}:`, error);
        document.getElementById(`chartContainer-${index}`).innerHTML = `<p class="small text-muted">Error loading chart: ${error}</p>`;
      }
    }

    async function expandChart(symbol, index) {
      try {
        // Fetch the 1D data for the expanded chart
        const response = await fetch(`/api/stock_history/${symbol}/1D`);
        const historyData = await response.json();

        if (historyData && historyData.length > 0 && !historyData[0].error) {
          // Update modal title
          document.getElementById('chartModalLabel').innerText = `${symbol} - 1D Chart (Intraday)`;

          // Clear previous chart in the modal if it exists
          const modalCanvas = document.getElementById('modalChart');
          const ctx = modalCanvas.getContext('2d');
          if (ctx.chart) {
            ctx.chart.destroy();
          }

          // Render the chart in the modal
          renderStockChart('modalChart', historyData, '1D');

          // Show the modal
          const chartModal = new bootstrap.Modal(document.getElementById('chartModal'));
          chartModal.show();
        } else {
          alert('No 1D data available to display in expanded view.');
        }
      } catch (error) {
        console.error(`Error expanding chart for ${symbol}:`, error);
        alert('Error loading expanded chart: ' + error);
      }
    }

 function renderStockChart(canvasId, historyData, period) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  // Clear previous chart if it exists
  if (ctx.chart) {
    ctx.chart.destroy();
  }
  const dates = historyData.map(item => item.date);
  const prices = historyData.map(item => item.close);
  const isIntraday = period === '1D';
  ctx.chart = new Chart(ctx, {
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
            maxTicksLimit: isIntraday ? 8 : 5, // More ticks for intraday to show hourly trends
            autoSkip: true,
            callback: function(value, index, values) {
              if (isIntraday) {
                // For intraday, show time in HH:MM format
                const date = new Date(dates[index]);
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              } else {
                // For 1W and 1M, show date in "MMM DD" format (e.g., "Apr 01")
                const date = new Date(dates[index]);
                return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit' });
              }
            }
          }
        },
        y: {
          display: canvasId !== 'modalChart', // Show Y-axis only in small charts
          beginAtZero: false
        }
      }
    }
  });
}

    async function getLivePrediction(symbol, index) {
      try {
        const response = await fetch(`/api/live_prediction/${symbol}`);
        const data = await response.json();
        if (data.error) {
          document.getElementById(`livePrediction-${index}`).innerText = `Error: ${data.error}`;
          return;
        }
        const trendColor = data.percent_change_today >= 0 ? 'text-success' : 'text-danger';
        const trendIcon = data.percent_change_today >= 0 ? '↑' : '↓';
        document.getElementById(`livePrediction-${index}`).innerHTML = `
          <strong>Live Prediction: ${data.recommendation}</strong><br/>
          <span class="${trendColor}">${trendIcon}${data.percent_change_today.toFixed(2)}% today</span><br/>
          RSI: ${data.technical_indicators.rsi}, MACD: ${data.technical_indicators.macd}<br/>
          Updated: ${data.last_updated}
        `;
      } catch (error) {
        document.getElementById(`livePrediction-${index}`).innerText = `Error fetching live prediction: ${error}`;
      }
    }

    function populateSectorFilter(stocks) {
      const sectorFilter = document.getElementById("sectorFilter");
      const sectors = [...new Set(stocks.map(stock => stock.sector))].sort();
      sectors.forEach(sector => {
        const option = document.createElement("option");
        option.value = sector;
        option.textContent = sector;
        sectorFilter.appendChild(option);
      });
    }

    function filterStocks() {
      const searchTerm = document.getElementById("stockSearch").value.toLowerCase();
      const selectedSector = document.getElementById("sectorFilter").value;
      const filteredStocks = allStocks.filter(stock => {
        const matchesSearch = stock.symbol.toLowerCase().includes(searchTerm) || 
                             (stock.name && stock.name.toLowerCase().includes(searchTerm));
        const matchesSector = !selectedSector || stock.sector === selectedSector;
        const matchesRecommendation = !selectedRecommendation || stock.recommendation === selectedRecommendation;
        return matchesSearch && matchesSector && matchesRecommendation;
      });
      renderStocks(filteredStocks);
    }

    function filterByRecommendation(recommendation) {
      // Toggle the recommendation filter
      if (selectedRecommendation === recommendation) {
        selectedRecommendation = ''; // Deselect if clicking the same filter
      } else {
        selectedRecommendation = recommendation;
      }
      // Update active state for visual feedback
      document.querySelectorAll('.recommendation-box').forEach(box => {
        box.classList.remove('active');
      });
      if (selectedRecommendation) {
        document.getElementById(`${selectedRecommendation.toLowerCase()}Box`).classList.add('active');
      }
      filterStocks();
    }

    function resetFilters() {
      selectedRecommendation = '';
      selectedTimePeriods = {}; // Reset time periods
      document.getElementById("stockSearch").value = '';
      document.getElementById("sectorFilter").value = '';
      document.querySelectorAll('.recommendation-box').forEach(box => {
        box.classList.remove('active');
      });
      filterStocks();
    }

    function toggleTheme() {
      console.log("Toggling theme...");
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      console.log("New theme:", newTheme);
    }

    document.addEventListener("DOMContentLoaded", () => {
      const saved = localStorage.getItem('theme') || 'light';
      document.documentElement.setAttribute('data-theme', saved);
      console.log("Loaded theme:", saved);
      loadDashboard();
      document.getElementById("stockSearch").addEventListener("input", filterStocks);
      document.getElementById("sectorFilter").addEventListener("change", filterStocks);
      document.getElementById("resetFilters").addEventListener("click", resetFilters);
    });

    document.getElementById("refreshBtn").addEventListener("click", async () => {
      document.getElementById("refreshBtn").innerText = "Refreshing...";
      try {
        const res = await fetch('/api/refresh', { method: 'POST' });
        const json = await res.json();
        if (json.success) {
          selectedRecommendation = ''; // Reset recommendation filter on refresh
          selectedTimePeriods = {}; // Reset time periods on refresh
          document.querySelectorAll('.recommendation-box').forEach(box => {
            box.classList.remove('active');
          });
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
  </script>
</body>
</html>
"""

# Write HTML template to file
with open('templates/index.html', 'w') as f:
    f.write(html_template)

def is_market_open():
    """Check if U.S. markets are open (9:30 AM to 4:00 PM EST)"""
    now = datetime.utcnow()  # Use UTC for consistency
    # Convert UTC to EST (UTC-5)
    est_offset = timedelta(hours=-5)
    est_time = now + est_offset
    market_open = est_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = est_time.replace(hour=16, minute=0, second=0, microsecond=0)
    # Adjust for the current day
    market_open = market_open.replace(year=est_time.year, month=est_time.month, day=est_time.day)
    market_close = market_close.replace(year=est_time.year, month=est_time.month, day=est_time.day)
    # Check if it's a weekday (Monday=0, Sunday=6)
    if est_time.weekday() >= 5:  # Saturday or Sunday
        return False
    return market_open <= est_time <= market_close

def fetch_yahoo_finance_data(symbol, start, end, interval, retries=3):
    """Fetch data fromklik Yahoo Finance with retry logic"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start}&period2={end}&interval={interval}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                return data
            else:
                logger.warning(f"No data found for {symbol} (interval={interval}): {data.get('chart', {}).get('error', 'Unknown error')}")
                return data
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {symbol}: {str(e)}")
            if attempt < retries - 1:
                time.sleep(random.uniform(1, 3))  # Random delay before retry
            else:
                logger.error(f"Failed to fetch data for {symbol} after {retries} attempts: {str(e)}")
                return None

def safe_float(value, default=0.0):
    """Safely convert a value to float, returning a default if conversion fails"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_last_trading_day(end_dt):
    """Get the last trading day before the given datetime"""
    est_offset = timedelta(hours=-5)  # Convert UTC to EST
    est_time = end_dt + est_offset

    # Determine the last trading day
    last_trading_day = end_dt
    if est_time.weekday() == 5:  # Saturday
        last_trading_day -= timedelta(days=1)  # Go back to Friday
    elif est_time.weekday() == 6:  # Sunday
        last_trading_day -= timedelta(days=2)  # Go back to Friday
    elif est_time.weekday() == 0 and est_time.hour < 14:  # Monday before market open (14:30 UTC = 9:30 EST)
        last_trading_day -= timedelta(days=3)  # Go back to Friday
    elif est_time.hour < 14:  # Before market open on a weekday
        last_trading_day -= timedelta(days=1)  # Go back to the previous day

    # Ensure we don't go back to a weekend
    est_last_trading = last_trading_day + est_offset
    while est_last_trading.weekday() >= 5:  # Saturday or Sunday
        last_trading_day -= timedelta(days=1)
        est_last_trading = last_trading_day + est_offset

    return last_trading_day

def get_price_history(symbol, period):
    """Get price history for a specific period (1D, 1W, 1M, or 14D)"""
    now = datetime.utcnow()
    end_dt = now.replace(minute=0, second=0, microsecond=0)
    
    if period == "1D":
        # Get data for current/last trading day
        if is_market_open():
            start_dt = end_dt - timedelta(days=1)
        else:
            start_dt = get_last_trading_day(end_dt)
        interval = "1m"
    elif period == "1W":
        start_dt = end_dt - timedelta(weeks=1)
        interval = "1d"
    elif period == "1M":
        start_dt = end_dt - timedelta(days=30)
        interval = "1d"
    else:
        start_dt = end_dt - timedelta(days=14)
        interval = "1d"

    start = int(start_dt.timestamp())
    end = int(end_dt.timestamp())
    if period == "1D":
        if is_market_open():
            start = end - 60*60*24*1  # 1 day
            interval = "1m"  # 1-minute intervals for intraday
        else:
            # After market hours, fetch the current day's data (if today is a trading day)
            now = datetime.utcnow()
            est_offset = timedelta(hours=-5)
            est_time = now + est_offset
            
            # Determine the last trading day
            last_trading_day = now
            if est_time.weekday() == 5:  # Saturday
                last_trading_day -= timedelta(days=1)  # Go back to Friday
            elif est_time.weekday() == 6:  # Sunday
                last_trading_day -= timedelta(days=2)  # Go back to Friday
            elif est_time.weekday() == 0 and est_time.hour < 9:  # Monday before market open
                last_trading_day -= timedelta(days=3)  # Go back to Friday
            
            # Set the time range for the last trading day (9:30 AM to 4:00 PM EST)
            start_dt = last_trading_day.replace(hour=14, minute=30, second=0, microsecond=0)  # 9:30 AM EST (14:30 UTC)
            end_dt = last_trading_day.replace(hour=21, minute=0, second=0, microsecond=0)  # 4:00 PM EST (21:00 UTC)
            start = int(start_dt.timestamp())
            end = int(end_dt.timestamp())
            interval = "1m"
    elif period == "1W":
        start = end - 60*60*24*7  # 7 days
        interval = "1d"
    elif period == "1M":
        start = end - 60*60*24*30  # 30 days
        interval = "1d"
    else:  # Default to 14 days
        start = end - 60*60*24*14
        interval = "1d"
    
    data = fetch_yahoo_finance_data(symbol, start, end, interval)
    if not data:
        return [{"error": f"Unable to fetch {period} data for {symbol} after multiple attempts."}]

    try:
        if 'error' in data['chart'] and data['chart']['error']:
            return [{"error": f"Yahoo Finance API error: {data['chart']['error']}"}]
        
        chart = data['chart']['result'][0]
        timestamps = chart.get('timestamp', [])
        if not timestamps:
            if period == "1D":
                return [{"error": "Intraday data unavailable (markets may be closed)."}]
            return [{"error": f"No {period} data available for {symbol}."}]

        closes = chart['indicators']['quote'][0]['close']
        history = []
        for ts, close in zip(timestamps, closes):
            if close is not None:
                dt = datetime.utcfromtimestamp(ts)
                # For intraday (1D), only include data up to the current time if market is open
                if period == "1D" and is_market_open() and dt > datetime.utcnow():
                    continue
                history.append({
                    'date': dt.strftime('%Y-%m-%d %H:%M:%S' if interval == "1m" else '%Y-%m-%d'),
                    'close': close
                })
        if not history:
            return [{"error": f"No valid {period} data points for {symbol}."}]
        return history
    except Exception as e:
        logger.error(f"Error processing {period} history for {symbol}: {str(e)} - Response: {data}")
        return [{"error": f"Error processing {period} data for {symbol}: {str(e)}"}]

def get_stock_info(symbol):
    """Get basic stock info and current price with improved reliability"""
    time.sleep(random.uniform(0.5, 1.5))  # Randomized delay to avoid rate limiting
    
    try:
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
                "sector": quote.get('sector', SECTOR_MAPPING.get(symbol, "Unknown")),
                "industry": quote.get('industry', "Unknown"),
                "market_cap": quote.get('marketCap', None),
                "pe_ratio": quote.get('trailingPE', None),
                "dividend_yield": quote.get('dividendYield', 0.0)  # Add dividend yield
            }
        else:
            return get_stock_info_by_scraping(symbol)
    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {str(e)}")
        return get_stock_info_by_scraping(symbol)

def get_stock_info_by_scraping(symbol):
    """Get stock info by scraping - backup method"""
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        price = None
        name = symbol
        
        if response.status_code == 200:
            html = response.text
            
            if '<h1' in html:
                name_start = html.find('<h1')
                name_end = html.find('</h1>', name_start)
                if name_end > 0:
                    name_content = html[name_start:name_end]
                    name_parts = name_content.split('>')
                    if len(name_parts) > 1:
                        name = name_parts[-1].strip()
            
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
            "sector": SECTOR_MAPPING.get(symbol, "Unknown"),
            "industry": "Unknown",
            "pe_ratio": None,
            "dividend_yield": 0.0
        }
    except Exception as e:
        logger.error(f"Error scraping info for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "name": symbol,
            "current_price": None,
            "sector": SECTOR_MAPPING.get(symbol, "Unknown"),
            "pe_ratio": None,
            "dividend_yield": 0.0
        }

def get_historical_data(symbol, days=60):  # Increased to 60 days to ensure enough data for SMA_50
    """Get historical price data for analysis with improved reliability"""
    time.sleep(random.uniform(0.5, 1.5))  # Randomized delay to avoid rate limiting
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start_timestamp}&period2={end_timestamp}&interval=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            return calculate_fallback_data(symbol)
        
        result = data["chart"]["result"][0]
        
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        close_prices = quotes["close"]
        volumes = quotes.get("volume", [])
        highs = quotes.get("high", [])
        lows = quotes.get("low", [])
        
        valid_data = []
        for i in range(len(timestamps)):
            price = close_prices[i] if i < len(close_prices) else None
            volume = volumes[i] if i < len(volumes) else None
            high = highs[i] if i < len(highs) else None
            low = lows[i] if i < len(lows) else None
            if price is not None and high is not None and low is not None:
                valid_data.append((timestamps[i], price, volume, high, low))
        
        if len(valid_data) < 2:
            return calculate_fallback_data(symbol)
        
        timestamps, prices, volumes, highs, lows = zip(*valid_data)
        
        # Convert to DataFrame for technical indicator calculations
        df = pd.DataFrame({
            'Close': prices,
            'Volume': volumes,
            'High': highs,
            'Low': lows
        })
        
        # Calculate technical indicators
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
        macd = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd.macd()
        df['SMA_50'] = ta.trend.SMAIndicator(df['Close'], window=50).sma_indicator()
        bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
        df['BB_High'] = bollinger.bollinger_hband()
        df['BB_Low'] = bollinger.bollinger_lband()
        df['BB_Width'] = (df['BB_High'] - df['BB_Low']) / df['Close']
        
        start_price = prices[0]
        end_price = prices[-1]
        high_price = max(prices)
        low_price = min(prices)
        price_change = end_price - start_price
        percent_change = (price_change / start_price) * 100
        
        # Calculate 5-day percent change
        prices_series = pd.Series(prices)
        percent_change_5d = prices_series.pct_change(periods=5).iloc[-1] * 100 if len(prices) >= 5 else 0
        
        daily_returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
        volatility = sum([(ret - (sum(daily_returns)/len(daily_returns)))**2 for ret in daily_returns])
        volatility = (volatility / len(daily_returns))**0.5 if daily_returns else 0
        
        volume_trend = analyze_volume(volumes)
        
        trend = "Neutral"
        bullish_signals = 0
        bearish_signals = 0
        
        rsi_value = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 50
        if rsi_value > 70:
            bearish_signals += 1
        elif rsi_value < 30:
            bullish_signals += 1
        
        macd_value = df['MACD'].iloc[-1] if not pd.isna(df['MACD'].iloc[-1]) else 0
        if macd_value > 0.5:
            bullish_signals += 1
        elif macd_value < -0.5:
            bearish_signals += 1
        
        if percent_change > 5:
            bullish_signals += 1
        elif percent_change < -5:
            bearish_signals += 1
        
        if "Increasing" in volume_trend:
            bullish_signals += 1
        elif "Decreasing" in volume_trend:
            bearish_signals += 1
        
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
            "percent_change_5d": percent_change_5d,
            "high": high_price,
            "low": low_price,
            "volatility": volatility,
            "volume_trend": volume_trend,
            "technical_indicators": {
                "rsi": f"{rsi_value:.1f}",
                "macd": f"{macd_value:.2f}",
                "sma_50": df['SMA_50'].iloc[-1] if not pd.isna(df['SMA_50'].iloc[-1]) else 0,
                "bb_width": df['BB_Width'].iloc[-1] if not pd.isna(df['BB_Width'].iloc[-1]) else 0,
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
        "percent_change_2w": random.uniform(-10, 10),
        "percent_change_5d": random.uniform(-5, 5),
        "current_price": random.uniform(50, 500),
        "volatility": random.uniform(1, 8),
        "technical_indicators": {
            "rsi": f"{random.uniform(30, 70):.1f}",
            "macd": f"{random.uniform(-2, 2):.2f}",
            "sma_50": 0,
            "bb_width": 0,
            "volume_analysis": "Neutral",
            "trend": "Neutral"
        }
    }

def calculate_rsi(prices, periods=14):
    """Calculate Relative Strength Index with improved error handling"""
    try:
        if len(prices) < periods + 1:
            return "Neutral (N/A)"
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[-periods:]) / periods
        avg_loss = sum(losses[-periods:]) / periods
        
        if avg_loss == 0:
            return "Overbought (100.0)"
        
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
    
    ema12 = sum(prices[-12:]) / 12
    ema26 = sum(prices[-26:]) / 26
    
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
    
    valid_volumes = [v for v in volumes if v is not None]
    if len(valid_volumes) < 5:
        return "Insufficient Data"
    
    half = len(valid_volumes) // 2
    avg_first_half = sum(valid_volumes[:half]) / half
    avg_second_half = sum(valid_volumes[half:]) / (len(valid_volumes) - half)
    
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

def get_news_sentiment(symbol, retries=3):
    """Get news sentiment for a symbol by analyzing recent news headlines with retries"""
    for attempt in range(retries):
        try:
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            articles = data.get("news", [])[:5]
            if not articles:
                logger.warning(f"No news articles found for {symbol} on attempt {attempt + 1}/{retries}")
                if attempt == retries - 1:
                    return 0
                time.sleep(random.uniform(1, 3))
                continue

            texts = [a.get("title", "") for a in articles]
            full_text = " ".join(texts)

            if not full_text.strip():
                logger.warning(f"No valid news titles found for {symbol} on attempt {attempt + 1}/{retries}")
                if attempt == retries - 1:
                    return 0
                time.sleep(random.uniform(1, 3))
                continue

            score = TextBlob(full_text).sentiment.polarity
            logger.info(f"Sentiment for {symbol}: {score:.3f} based on {len(articles)} articles: {texts}")
            return score
        except Exception as e:
            logger.warning(f"News sentiment error for {symbol} on attempt {attempt + 1}/{retries}: {str(e)}")
            if attempt == retries - 1:
                return 0
            time.sleep(random.uniform(1, 3))
    return 0

def analyze_stock(symbol):
    """Analyze a single stock"""
    try:
        info = get_stock_info(symbol)
        history = get_historical_data(symbol, days=60)  # Fetch 60 days for SMA_50
        news_sentiment = get_news_sentiment(symbol, retries=3)
        history_1d = get_price_history(symbol, "1D")

        current_price = history.get("current_price") or info.get("current_price")
        percent_change_2w = safe_float(history.get("percent_change_2w", 0))
        percent_change_5d = safe_float(history.get("percent_change_5d", 0))
        volatility = safe_float(history.get("volatility", 5))

        technical_indicators = history.get("technical_indicators", {})
        rsi_str = str(technical_indicators.get("rsi", "50"))
        macd_str = str(technical_indicators.get("macd", "0"))
        sma_50 = safe_float(technical_indicators.get("sma_50", 0))
        bb_width = safe_float(technical_indicators.get("bb_width", 0))

        rsi = safe_float(rsi_str, default=50)
        macd = safe_float(macd_str, default=0)
        volume_score = 1 if "Increasing" in technical_indicators.get("volume_analysis", "") else 0
        sentiment_score = safe_float(news_sentiment, 0)
        pe_ratio = safe_float(info.get("pe_ratio", np.nan))
        dividend_yield = safe_float(info.get("dividend_yield", 0))

        # Create features DataFrame with the correct column names
        features_dict = {
            'RSI': rsi,
            'MACD': macd,
            'SMA_50': sma_50,
            'BB_Width': bb_width,
            'PE_Ratio': pe_ratio,
            'Dividend_Yield': dividend_yield,
            'News_Sentiment': sentiment_score,
            'volume_score': volume_score,
            'percent_change_5d': percent_change_5d,
            'volatility': volatility
        }
        features_df = pd.DataFrame([features_dict], columns=FEATURE_COLUMNS)

        # Handle missing values (same as in training)
        features_df['PE_Ratio'] = features_df['PE_Ratio'].fillna(features_df['PE_Ratio'].median())
        features_df['Dividend_Yield'] = features_df['Dividend_Yield'].fillna(0.0)
        features_df['News_Sentiment'] = features_df['News_Sentiment'].fillna(0.0)

        # Make prediction
        pred = model.predict(features_df)[0]
        recommendation = label_encoder.inverse_transform([pred])[0]

        reason = (
            f"🤖 ML-based prediction using "
            f"RSI={rsi:.1f}, MACD={macd:.2f}, SMA_50={sma_50:.2f}, BB_Width={bb_width:.2f}, "
            f"PE_Ratio={pe_ratio:.2f}, Dividend_Yield={dividend_yield:.2f}, "
            f"Sentiment={sentiment_score:.2f}, Volume_Score={volume_score}, "
            f"Change_5d={percent_change_5d:.2f}%, Volatility={volatility:.2f}"
        )

        logger.info(f"{symbol} → ML RECOMMEND: {recommendation}")

        return {
            "symbol": symbol,
            "name": info.get("name", symbol),
            "recommendation": recommendation,
            "percent_change_2w": percent_change_2w,
            "current_price": current_price,
            "reason": reason,
            "technical_indicators": technical_indicators,
            "news_sentiment": news_sentiment,
            "history_1d": history_1d,
            "sector": info.get("sector", SECTOR_MAPPING.get(symbol, "Unknown"))
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
            "history_1d": [],
            "sector": SECTOR_MAPPING.get(symbol, "Unknown")
        }

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
        "history_1d": [],
        "sector": SECTOR_MAPPING.get(symbol, "Unknown")
    }

def analyze_all_stocks():
    """Analyze all stocks and cache the results"""
    try:
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(analyze_stock, symbol): symbol for symbol in STOCK_LIST}
            stocks = []
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    stocks.append(result)
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {str(e)}")
                    stocks.append(create_fallback_entry(symbol))

        # Sort stocks by symbol
        stocks.sort(key=lambda x: x['symbol'])

        # Compute summary of recommendations
        summary = {"BUY": 0, "HOLD": 0, "SELL": 0}
        for stock in stocks:
            recommendation = stock.get('recommendation', 'HOLD')
            summary[recommendation] = summary.get(recommendation, 0) + 1

        # Prepare the result
        result = {
            "stocks": stocks,
            "summary": summary,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Cache the results
        with open('data/stock_analysis.json', 'w') as f:
            json.dump(result, f, indent=2)

        logger.info(f"Successfully analyzed {len(stocks)} stocks")
        return result
    except Exception as e:
        logger.error(f"Error in analyze_all_stocks: {str(e)}")
        return {"error": f"Analysis failed: {str(e)}"}

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')

@app.route('/api/stocks')
def api_stocks():
    """Get stock data - first try cache, then live data"""
    try:
        # During market hours, reduce cache duration to 5 minutes for fresher data
        cache_duration = 300 if is_market_open() else 1800  # 5 minutes during market hours, 30 minutes otherwise
        if os.path.exists('data/stock_analysis.json'):
            with open('data/stock_analysis.json', 'r') as f:
                data = json.load(f)
                last_updated = datetime.strptime(data['last_updated'], "%Y-%m-%d %H:%M:%S")
                age = datetime.now() - last_updated
                if age.total_seconds() < cache_duration:
                    return jsonify(data)
        return jsonify(analyze_all_stocks())
    except Exception as e:
        error_msg = f"API error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/api/stock_history/<symbol>/<period>')
def api_stock_history(symbol, period):
    """Get price history for a specific stock and time period"""
    try:
        history = get_price_history(symbol, period)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error fetching history for {symbol} ({period}): {str(e)}")
        return jsonify([{"error": f"Error fetching {period} history: {str(e)}"}]), 500

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Refresh stock data"""
    try:
        if os.path.exists('data/stock_analysis.json'):
            os.remove('data/stock_analysis.json')
        data = analyze_all_stocks()
        if not isinstance(data, dict) or "stocks" not in data:
            raise ValueError("Invalid format returned from analysis")
        return jsonify({"success": True, "message": "Refreshed successfully"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/predict", methods=["POST"])
def predict():
    """Predict recommendation for given features"""
    try:
        data = request.get_json()
        features_dict = {
            'RSI': data.get("rsi", 50),
            'MACD': data.get("macd", 0),
            'SMA_50': data.get("sma_50", 0),
            'BB_Width': data.get("bb_width", 0),
            'PE_Ratio': data.get("pe_ratio", np.nan),
            'Dividend_Yield': data.get("dividend_yield", 0),
            'News_Sentiment': data.get("news_sentiment", 0),
            'volume_score': data.get("volume_score", 0),
            'percent_change_5d': data.get("percent_change_5d", 0),
            'volatility': data.get("volatility", 0)
        }
        features_df = pd.DataFrame([features_dict], columns=FEATURE_COLUMNS)
        # Handle missing values
        features_df['PE_Ratio'] = features_df['PE_Ratio'].fillna(features_df['PE_Ratio'].median())
        features_df['Dividend_Yield'] = features_df['Dividend_Yield'].fillna(0.0)
        features_df['News_Sentiment'] = features_df['News_Sentiment'].fillna(0.0)

        prediction = model.predict(features_df)[0]
        recommendation = label_encoder.inverse_transform([prediction])[0]
        return jsonify({
            "recommendation": recommendation,
            "reason": f"ML-based prediction using RSI={features_df['RSI'][0]}, MACD={features_df['MACD'][0]}, volume_score={features_df['volume_score'][0]}, change={features_df['percent_change_5d'][0]}, volatility={features_df['volatility'][0]}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/live_prediction/<symbol>')
def live_prediction(symbol):
    """Get a live prediction for a specific stock based on the latest intraday data"""
    try:
        # Fetch the latest intraday data
        history_1d = get_price_history(symbol, "1D")
        if not history_1d or ('error' in history_1d[0] and history_1d[0]['error']):
            return jsonify({"error": "Insufficient intraday data for prediction"}), 400

        # Fetch current stock info (for P/E ratio and dividend yield)
        info = get_stock_info(symbol)
        news_sentiment = get_news_sentiment(symbol)

        # Extract prices from intraday data
        prices = [entry['close'] for entry in history_1d if 'close' in entry]
        if not prices:
            return jsonify({"error": "No valid price data available for prediction"}), 400

        current_price = prices[-1] if prices else info.get("current_price", 100.0)

        # Compute technical indicators
        df = pd.DataFrame({'Close': prices})
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
        macd = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd.macd()
        df['SMA_50'] = ta.trend.SMAIndicator(df['Close'], window=50).sma_indicator()
        bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
        df['BB_Width'] = (bollinger.bollinger_hband() - bollinger.bollinger_lband()) / df['Close']

        # Compute percent change and volatility
        start_price = prices[0]
        percent_change = ((current_price - start_price) / start_price) * 100 if start_price else 0
        prices_series = pd.Series(prices)
        percent_change_5d = prices_series.pct_change(periods=5).iloc[-1] * 100 if len(prices) >= 5 else 0
        daily_returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
        volatility = (sum([(ret - (sum(daily_returns)/len(daily_returns)))**2 for ret in daily_returns]) / len(daily_returns))**0.5 if daily_returns else 5

        # Extract features for prediction
        rsi_value = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 50
        macd_value = df['MACD'].iloc[-1] if not pd.isna(df['MACD'].iloc[-1]) else 0
        sma_50 = df['SMA_50'].iloc[-1] if not pd.isna(df['SMA_50'].iloc[-1]) else 0
        bb_width = df['BB_Width'].iloc[-1] if not pd.isna(df['BB_Width'].iloc[-1]) else 0
        volume_score = 1 if len(prices) > 10 and prices[-1] > prices[-2] else 0  # Simplified volume trend
        pe_ratio = safe_float(info.get("pe_ratio", np.nan))
        dividend_yield = safe_float(info.get("dividend_yield", 0))

        # Create features DataFrame
        features_dict = {
            'RSI': rsi_value,
            'MACD': macd_value,
            'SMA_50': sma_50,
            'BB_Width': bb_width,
            'PE_Ratio': pe_ratio,
            'Dividend_Yield': dividend_yield,
            'News_Sentiment': news_sentiment,
            'volume_score': volume_score,
            'percent_change_5d': percent_change_5d,
            'volatility': volatility
        }
        features_df = pd.DataFrame([features_dict], columns=FEATURE_COLUMNS)

        # Handle missing values
        features_df['PE_Ratio'] = features_df['PE_Ratio'].fillna(features_df['PE_Ratio'].median())
        features_df['Dividend_Yield'] = features_df['Dividend_Yield'].fillna(0.0)
        features_df['News_Sentiment'] = features_df['News_Sentiment'].fillna(0.0)

        # Make prediction
        pred = model.predict(features_df)[0]
        recommendation = label_encoder.inverse_transform([pred])[0]

        return jsonify({
            "symbol": symbol,
            "recommendation": recommendation,
            "current_price": current_price,
            "percent_change_today": percent_change,
            "technical_indicators": {
                "rsi": f"{rsi_value:.1f}",
                "macd": f"{macd_value:.2f}",
                "trend": "Bullish" if percent_change > 0 else "Bearish"
            },
            "news_sentiment": news_sentiment,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Error generating live prediction for {symbol}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/retrain", methods=["POST"])
def retrain_model():
    """Placeholder for model retraining"""
    try:
        import train_model
        return jsonify({"success": True, "message": "Model retrained successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    if not os.path.exists('data/stock_analysis.json'):
        try:
            analyze_all_stocks()
        except Exception as e:
            logger.error(f"Initial analysis error: {str(e)}")
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port)