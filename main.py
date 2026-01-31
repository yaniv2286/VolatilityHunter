from flask import Flask, jsonify, render_template_string
from datetime import datetime
import sys
import os
from src.config import PORT, STOCK_LIST, STOCK_UNIVERSE_MODE, TICKER_FILTERS, TICKER_LIST_FILE, DATA_SOURCE
from src.data_loader import get_stock_data
from src.data_loader_factory import get_data_loader
from src.strategy import scan_all_stocks, get_portfolio_summary
from src.notifications import log_info, log_error
from src.ticker_manager import TickerManager

app = Flask(__name__)
ticker_manager = TickerManager()
data_loader = get_data_loader()

def get_active_stock_list():
    """Get the active stock list based on configuration."""
    if STOCK_UNIVERSE_MODE == 'all':
        # Load from file or get full universe
        if os.path.exists(TICKER_LIST_FILE):
            return ticker_manager.load_ticker_list(TICKER_LIST_FILE)
        else:
            # Use data source to get and filter tickers
            if DATA_SOURCE == 'yfinance':
                all_tickers = data_loader.download_nasdaq_tickers()
                filtered_df = data_loader.filter_tickers_by_criteria(
                    all_tickers,
                    min_price=TICKER_FILTERS['min_price'],
                    min_volume=TICKER_FILTERS['min_volume']
                )
                tickers = filtered_df['ticker'].tolist()
            else:
                tickers = ticker_manager.get_filtered_tickers(
                    min_price=TICKER_FILTERS['min_price'],
                    min_volume=TICKER_FILTERS['min_volume'],
                    exchanges=TICKER_FILTERS['exchanges']
                )
            ticker_manager.save_ticker_list(tickers, TICKER_LIST_FILE)
            return tickers
    elif STOCK_UNIVERSE_MODE == 'sp500':
        return ticker_manager.get_sp500_tickers()
    else:
        # Default to manual list
        return STOCK_LIST

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>VolatilityHunter Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 {
            color: #667eea;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .status {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            margin: 10px 5px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #5568d3;
        }
        .btn-success {
            background: #28a745;
        }
        .btn-success:hover {
            background: #218838;
        }
        .actions {
            text-align: center;
            margin: 30px 0;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .info-card {
            background: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }
        .info-card h3 {
            margin: 0 0 10px 0;
            color: #667eea;
            font-size: 2em;
        }
        .info-card p {
            margin: 0;
            color: #666;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #999;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 VolatilityHunter</h1>
        <p class="subtitle">Swing Trading Bot - Wealth Builder Strategy</p>
        
        <div class="status">
            <h2>📊 System Status</h2>
            <div class="info-grid">
                <div class="info-card">
                    <h3>{{ stock_count }}</h3>
                    <p>Tracked Stocks</p>
                </div>
                <div class="info-card">
                    <h3>✓</h3>
                    <p>System Online</p>
                </div>
                <div class="info-card">
                    <h3>SMA 200</h3>
                    <p>Trend Filter</p>
                </div>
                <div class="info-card">
                    <h3>32-80</h3>
                    <p>Sweet Spot</p>
                </div>
            </div>
        </div>

        <div class="actions">
            <h2>🚀 Actions</h2>
            <a href="/update" class="btn">Update Market Data</a>
            <a href="/scan" class="btn btn-success">Scan for Signals</a>
        </div>

        <div class="status">
            <h3>📈 Strategy Details</h3>
            <ul>
                <li><strong>Entry:</strong> Price > SMA 200 AND Stochastic K between 32-80</li>
                <li><strong>Exit:</strong> Price < SMA 200 (Trend Break)</li>
                <li><strong>Filter:</strong> Only stocks with CAGR > 15%</li>
                <li><strong>Indicators:</strong> SMA 200, Stochastic (10,3,3)</li>
            </ul>
        </div>

        <div class="footer">
            <p>VolatilityHunter v1.0 | {{ timestamp }}</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    active_stocks = get_active_stock_list()
    return render_template_string(
        HTML_DASHBOARD,
        stock_count=len(active_stocks),
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/update')
def update():
    try:
        log_info("Received /update request")
        active_stocks = get_active_stock_list()
        result = data_loader.update_all_stocks(stock_list=active_stocks, full_refresh=False)
        return jsonify(result), 200
    except Exception as e:
        log_error(f"Error in /update endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/update/full')
def update_full():
    try:
        log_info("Received /update/full request")
        active_stocks = get_active_stock_list()
        result = data_loader.update_all_stocks(stock_list=active_stocks, full_refresh=True)
        return jsonify(result), 200
    except Exception as e:
        log_error(f"Error in /update/full endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/scan')
def scan():
    try:
        log_info("Received /scan request")
        active_stocks = get_active_stock_list()
        
        stock_data = {}
        for ticker in active_stocks:
            df = get_stock_data(ticker)
            if df is not None:
                stock_data[ticker] = df
        
        scan_results = scan_all_stocks(stock_data)
        summary = get_portfolio_summary(scan_results)
        
        response = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'signals': scan_results
        }
        
        return jsonify(response), 200
    except Exception as e:
        log_error(f"Error in /scan endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/tickers/refresh')
def refresh_tickers():
    """Refresh the ticker list based on current configuration."""
    try:
        log_info("Received /tickers/refresh request")
        
        if STOCK_UNIVERSE_MODE == 'all':
            tickers = ticker_manager.get_filtered_tickers(
                min_price=TICKER_FILTERS['min_price'],
                min_volume=TICKER_FILTERS['min_volume'],
                exchanges=TICKER_FILTERS['exchanges']
            )
            ticker_manager.save_ticker_list(tickers, TICKER_LIST_FILE)
            message = f"Refreshed ticker list with {len(tickers)} stocks"
        elif STOCK_UNIVERSE_MODE == 'sp500':
            tickers = ticker_manager.get_sp500_tickers()
            message = f"Using S&P 500 universe with {len(tickers)} stocks"
        else:
            tickers = STOCK_LIST
            message = f"Using manual list with {len(tickers)} stocks"
        
        return jsonify({
            'success': True,
            'message': message,
            'ticker_count': len(tickers),
            'mode': STOCK_UNIVERSE_MODE,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        log_error(f"Error refreshing tickers: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/tickers/list')
def list_tickers():
    """Get the current list of active tickers."""
    try:
        active_stocks = get_active_stock_list()
        return jsonify({
            'success': True,
            'tickers': active_stocks,
            'count': len(active_stocks),
            'mode': STOCK_UNIVERSE_MODE,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        log_error(f"Error listing tickers: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def cli_update(full=False):
    print(f"{'='*60}")
    print(f"VolatilityHunter - Data Update ({'Full' if full else 'Incremental'})")
    print(f"{'='*60}")
    print(f"Data Source: {DATA_SOURCE}")
    active_stocks = get_active_stock_list()
    print(f"Stock Universe: {STOCK_UNIVERSE_MODE} ({len(active_stocks)} stocks)")
    result = data_loader.update_all_stocks(stock_list=active_stocks, full_refresh=full)
    print(f"\n✓ Update Complete:")
    print(f"  - Updated: {result['updated']}/{result['total']} stocks")
    print(f"  - Timestamp: {result['timestamp']}")
    print(f"{'='*60}\n")

def cli_scan():
    print(f"{'='*60}")
    print("VolatilityHunter - Market Scan")
    print(f"{'='*60}")
    print(f"Data Source: {DATA_SOURCE}")
    active_stocks = get_active_stock_list()
    print(f"Stock Universe: {STOCK_UNIVERSE_MODE} ({len(active_stocks)} stocks)")
    
    stock_data = {}
    for ticker in active_stocks:
        df = get_stock_data(ticker)
        if df is not None:
            stock_data[ticker] = df
    
    scan_results = scan_all_stocks(stock_data)
    summary = get_portfolio_summary(scan_results)
    
    print(f"\n📊 SUMMARY:")
    print(f"  - Total Stocks: {summary['total_stocks']}")
    print(f"  - BUY Signals: {summary['buy_signals']}")
    print(f"  - SELL Signals: {summary['sell_signals']}")
    print(f"  - HOLD Signals: {summary['hold_signals']}")
    print(f"  - Errors: {summary['errors']}")
    
    if summary['buy_signals'] > 0:
        print(f"\n🟢 BUY SIGNALS:")
        for signal in scan_results['BUY']:
            print(f"  - {signal['ticker']}: ${signal['indicators']['price']:.2f}")
            print(f"    Reason: {signal['reason']}")
    
    if summary['sell_signals'] > 0:
        print(f"\n🔴 SELL SIGNALS:")
        for signal in scan_results['SELL']:
            print(f"  - {signal['ticker']}: ${signal['indicators']['price']:.2f}")
            print(f"    Reason: {signal['reason']}")
    
    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'update':
            cli_update(full=False)
        elif command == 'update-full':
            cli_update(full=True)
        elif command == 'scan':
            cli_scan()
        else:
            print("Unknown command. Available commands: update, update-full, scan")
    else:
        log_info(f"Starting VolatilityHunter Flask server on port {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
