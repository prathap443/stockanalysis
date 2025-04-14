from flask import Flask, render_template, jsonify, send_from_directory
import requests
import json
import os
import time
from datetime import datetime, timedelta
import logging
import random

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Create directories
os.makedirs('templates', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Expanded list of 20 major stocks
STOCK_LIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", 
    "TSLA", "NVDA", "JPM", "V", "WMT", 
    "DIS", "NFLX", "PYPL", "INTC", "AMD", 
    "BA", "PFE", "KO", "PEP", "XOM"
]

# HTML template for the dashboard
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Market Dashboard - Prathap's Analysis</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- ... (keep existing styles unchanged) ... -->
</head>
<body>
    <!-- ... (keep existing HTML structure unchanged) ... -->
    
    <script>
        // ... (existing JavaScript code remains the same until displayStocks) ...

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
                
                // Format technical indicators
                let technicalHtml = '';
                if (stock.technical_indicators) {
                    technicalHtml = `
                        <div class="tech-indicators mt-2">
                            <div class="row">
                                <div class="col-6 indicator">RSI: <strong>${stock.technical_indicators.rsi || 'N/A'}</strong></div>
                                <div class="col-6 indicator">MACD: <strong>${stock.technical_indicators.macd || 'N/A'}</strong></div>
                                <div class="col-6 indicator">Volume: <strong>${stock.technical_indicators.volume_analysis || 'N/A'}</strong></div>
                                <div class="col-6 indicator">Trend: <strong>${stock.technical_indicators.trend || 'N/A'}</strong></div>
                            </div>
                        </div>
                    `;
                }
                
                // Format news
                let newsHtml = '';
                if (stock.news_sentiment) {
                    newsHtml = `<p class="mt-2 small"><strong>News Sentiment:</strong> ${stock.news_sentiment}</p>`;
                }
                
                // Safely handle prices and percentages
                const currentPrice = stock.current_price !== undefined && stock.current_price !== null 
                    ? stock.current_price.toFixed(2) 
                    : 'N/A';
                    
                const percentChange = stock.percent_change_2w !== undefined && stock.percent_change_2w !== null
                    ? (stock.percent_change_2w >= 0 ? '+' : '') + stock.percent_change_2w.toFixed(2)
                    : '0.00';

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
                                    <h4>$${currentPrice}</h4>
                                </div>
                                <div class="text-end">
                                    <h5 class="${changeClass}">
                                        ${percentChange}%
                                    </h5>
                                    <small class="text-muted">2-week change</small>
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <p>${stock.reason || ''}</p>
                                ${newsHtml}
                                ${technicalHtml}
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
    f.write(html_template)

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
        
        # Check if response is JSON before parsing
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type and 'text/javascript' not in content_type:
            logger.warning(f"Non-JSON response for {symbol}. Falling back to scraping.")
            return get_stock_info_by_scraping(symbol)
            
        try:
            data = response.json()
        except ValueError:
            logger.warning(f"Invalid JSON for {symbol}. Falling back to scraping.")
            return get_stock_info_by_scraping(symbol)
        
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
            
            # Extract name
            if '<h1' in html:
                name_start = html.find('<h1')
                name_end = html.find('</h1>', name_start)
                if name_end > 0:
                    name_content = html[name_start:name_end]
                    name_parts = name_content.split('>')
                    if len(name_parts) > 1:
                        name = name_parts[-1].split('<!--')[0].strip()
            
            # Extract price - look for regularMarketPrice
            price_marker = 'data-field="regularMarketPrice"'
            if price_marker in html:
                price_pos = html.find(price_marker)
                value_attr = 'value="'
                value_start = html.find(value_attr, price_pos)
                if value_start > 0:
                    value_start += len(value_attr)
                    value_end = html.find('"', value_start)
                    if value_end > value_start:
                        price_str = html[value_start:value_end]
                        try:
                            price = float(price_str.replace(',', ''))
                        except Exception:
                            price = None
        
        return {
            "symbol": symbol,
            "name": name,
            "current_price": price,
            "sector": "Unknown",
            "industry": "Unknown",
            "market_cap": None,
            "pe_ratio": None
        }
    except Exception as e:
        logger.error(f"Scraping failed for {symbol}: {str(e)}")
        return {
            "symbol": symbol,
            "name": symbol,
            "current_price": None,
            "sector": "Unknown",
            "industry": "Unknown",
            "market_cap": None,
            "pe_ratio": None
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stocks')
def api_stocks():
    try:
        # Example data structure - replace with actual data fetching logic
        data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {"BUY": 5, "HOLD": 10, "SELL": 5},
            "stocks": [{
                "symbol": stock,
                "name": "Example Corp",
                "current_price": 150.50,
                "percent_change_2w": 2.5,
                "recommendation": random.choice(["BUY", "SELL", "HOLD"]),
                "reason": "Strong market position",
                "news_sentiment": "Positive",
                "technical_indicators": {
                    "rsi": 45.2,
                    "macd": "Bullish",
                    "volume_analysis": "Average",
                    "trend": "Upward"
                }
            } for stock in STOCK_LIST]
        }
        return jsonify(data)
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({"error": "Failed to load stock data."}), 500

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    try:
        # Add actual data refresh logic here
        return jsonify({"success": True, "message": "Data refreshed successfully"})
    except Exception as e:
        logger.error(f"Refresh error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
