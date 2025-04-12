"""
WSGI entry point for Gunicorn
"""
from stock_analysis_webapp import app

# This is what Gunicorn imports
if __name__ == "__main__":
    app.run()