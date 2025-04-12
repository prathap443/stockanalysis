"""
Simple and Robust Stock Analysis App
"""

from flask import Flask, render_template, jsonify, send_from_directory
import requests
import json
import os
import time
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Create directories
os.makedirs('templates', exist_ok=True)
os.makedirs('data', exist_ok=True)

# HTML template - unchanged from your existing code
html_template = """
<!DOCTYPE html>
<html lang="en">
<!-- Your existing HTML template -->
</html>
"""

# Write HTML template to file
with open('templates/index.html', 'w') as f:
    f.write(html_template)

# Fixed list of major stocks to analyze
STOCK_LIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]

def get_stock_info(symbol):
    """Get stock info directly via Yahoo Finance API instead of scraping"""
    time.sleep(1)  # Avoid rate limiting
    try:
        # Use Yahoo Finance API directly
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        if 'quoteResponse' in data and 'result' in data['quoteResponse'] and len(data['quoteResponse']['result']) > 0:
            quote = data['quoteResponse']['result'][0]
            return {
                "symbol": symbol,
                "name": quote.get('shortName', symbol),
                "current_price": quote.get('regularMarketPrice', None)
            }
        
        raise Exception(f"No data found for {symbol}")
    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {str(e)}")
        # Return minimal info rather than failing
        return {
            "symbol": symbol,
            "name": symbol,
            "current_price": None
        }

def get_historical_data(symbol, days=14):
    """Get historical price data for analysis"""
    time.sleep(1)  # Avoid rate limiting
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for Yahoo Finance API
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        # Using Yahoo Finance API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start_timestamp}&period2={end_timestamp}&interval=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            return {
                "symbol": symbol,
                "error": "No data returned",
                "percent_change_2w": 0,
                "current_price": None
            }
        
        result = data["chart"]["result"][0]
        
        # Extract price data
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        close_prices = quotes["close"]
        
        # Filter out None values
        valid_prices = [p for p in close_prices if p is not None]
        
        if len(valid_prices) < 2:
            return {
                "symbol": symbol,
                "error": "Insufficient price data",
                "percent_change_2w": 0,
                "current_price": valid_prices[0] if valid_prices else None
            }
        
        # Calculate metrics
        start_price = valid_prices[0]
        end_price = valid_prices[-1]
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
        logger.error(f"Error getting history for {symbol}: {str(e)}")
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
    
    # Handle errors gracefully
    if "error" in history:
        logger.warning(f"Error in historical data for {symbol}: {history['error']}")
        
        # Try to use current price from info if available
        if info.get("current_price"):
            history["current_price"] = info["current_price"]
            history["percent_change_2w"] = 0  # Default to neutral
            del history["error"]  # Remove error to continue analysis
        else:
            return {
                "symbol": symbol,
                "name": info.get("name", symbol),
                "recommendation": "HOLD",  # Default to HOLD on error
                "reason": "Insufficient data to make a recommendation.",
                "current_price": info.get("current_price"),
                "percent_change_2w": 0
            }
    
    # Extract key metrics
    percent_change = history.get("percent_change_2w", 0)
    current_price = history.get("current_price") or info.get("current_price")
    
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
    """Analyze all stocks from our fixed list"""
    logger.info("Starting stock analysis...")
    
    results = []
    recommendations = {"BUY": 0, "HOLD": 0, "SELL": 0, "UNKNOWN": 0}
    
    for symbol in STOCK_LIST:
        try:
            logger.info(f"Analyzing {symbol}...")
            analysis = analyze_stock(symbol)
            recommendations[analysis.get("recommendation", "UNKNOWN")] += 1
            results.append(analysis)
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            # Add basic entry on error
            results.append({
                "symbol": symbol,
                "name": symbol,
                "recommendation": "HOLD",
                "percent_change_2w": 0,
                "current_price": None,
                "reason": "Analysis failed due to technical issues."
            })
            recommendations["UNKNOWN"] += 1
    
    # Save data to file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "stocks": results,
        "summary": recommendations,
        "last_updated": timestamp
    }
    
    try:
        with open('data/stock_analysis.json', 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving analysis to file: {str(e)}")
    
    logger.info(f"Analysis complete. Analyzed {len(results)} stocks.")
    return data

@app.route('/')
def index():
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
    """Force refresh stock data"""
    try:
        data = analyze_all_stocks()
        # Validate the result is actually in the correct format
        if not isinstance(data, dict) or "stocks" not in data:
            return jsonify({"success": False, "error": "Invalid analysis result format"}), 500
        return jsonify({"success": True, "message": "Data refreshed"})
    except Exception as e:
        error_msg = f"Refresh error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500

if __name__ == "__main__":
    # Initial data load if no existing data
    if not os.path.exists('data/stock_analysis.json'):
        try:
            analyze_all_stocks()
        except Exception as e:
            logger.error(f"Initial analysis error: {str(e)}")
    
    # Start the web server
    app.run(host='0.0.0.0', port=5000)