"""
WSGI entry point for Gunicorn
"""
from stock_analysis_webapp import app  # Import just the Flask app instance

# This is what Gunicorn imports
# No need to call app.run() here as Gunicorn will handle that