"""
WSGI entry point for Gunicorn
"""
from stock_analysis_webapp import app, analyze_all_stocks  # only keep analyze_all_stocks if truly needed
import threading
import time
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create necessary directories
os.makedirs('data', exist_ok=True)
os.makedirs('templates', exist_ok=True)

def startup():
    """Run startup tasks like loading initial analysis"""
    try:
        analyze_all_stocks()
        logger.info("Initial stock analysis completed")
    except Exception as e:
        logger.error(f"Initial analysis error: {str(e)}")

def refresh_data_periodically():
    """Background task to refresh stock data every hour"""
    while True:
        try:
            time.sleep(3600)  # 1 hour
            logger.info("Auto-refreshing stock data...")
            analyze_all_stocks()
            logger.info("Auto-refresh complete.")
        except Exception as e:
            logger.error(f"Error in auto-refresh: {str(e)}")

# Only start background tasks if running as main
if __name__ != "__gunicorn__":
    startup()
    refresh_thread = threading.Thread(target=refresh_data_periodically, daemon=True)
    refresh_thread.start()
