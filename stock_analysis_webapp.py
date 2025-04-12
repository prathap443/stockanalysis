"""
Minimal Stock Analysis Web App
"""

from flask import Flask, send_from_directory
import os

# Initialize Flask app
app = Flask(__name__)

# Ensure directories exist
os.makedirs('static', exist_ok=True)

# Create a simple HTML file directly
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Market Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container my-4">
        <h1 class="mb-4">Stock Market Dashboard</h1>
        <p class="text-muted">Analysis of top stocks based on performance and technical indicators</p>
        
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="card text-center bg-light">
                    <div class="card-body">
                        <h5 class="card-title text-success">Buy</h5>
                        <p class="display-4">1</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center bg-light">
                    <div class="card-body">
                        <h5 class="card-title text-warning">Hold</h5>
                        <p class="display-4">9</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center bg-light">
                    <div class="card-body">
                        <h5 class="card-title text-danger">Sell</h5>
                        <p class="display-4">0</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row row-cols-1 row-cols-md-2 g-4">
            <div class="col">
                <div class="card bg-success bg-opacity-25">
                    <div class="card-body">
                        <h3 class="card-title">AAPL</h3>
                        <h6 class="card-subtitle mb-2 text-muted">Apple Inc.</h6>
                        <div class="d-flex justify-content-between">
                            <h4>$198.15</h4>
                            <div class="text-danger text-end">-10.80%</div>
                        </div>
                        <p>Significant drop may represent a buying opportunity if fundamentals remain strong.</p>
                        <span class="badge bg-success">BUY</span>
                    </div>
                </div>
            </div>
            <div class="col">
                <div class="card bg-warning bg-opacity-25">
                    <div class="card-body">
                        <h3 class="card-title">MSFT</h3>
                        <h6 class="card-subtitle mb-2 text-muted">Microsoft Corporation</h6>
                        <div class="d-flex justify-content-between">
                            <h4>$388.45</h4>
                            <div class="text-success text-end">+3.48%</div>
                        </div>
                        <p>Good performance but not extreme enough to change position.</p>
                        <span class="badge bg-warning">HOLD</span>
                    </div>
                </div>
            </div>
            <!-- More stock cards would go here -->
        </div>
        
        <div class="mt-5 text-center text-muted small">
            <p>Data for informational purposes only. Not financial advice.</p>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Simple routes that always work
@app.route('/')
def index():
    # Write the HTML content to a file
    with open('index.html', 'w') as f:
        f.write(html_content)
    # Serve the file directly
    return html_content

# Create a simple app object for WSGI
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)