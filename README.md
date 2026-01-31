# 🎯 VolatilityHunter

A production-ready algorithmic trading bot that implements the "Wealth Builder" swing trading strategy for volatile tech stocks. Built with Python, Flask, and designed for deployment on Google Cloud Run.

## 📊 Strategy Overview

**Wealth Builder Strategy:**
- **Entry Rule:** Price > SMA 200 AND Stochastic K between 32-80 (The Sweet Spot)
- **Exit Rule:** Price < SMA 200 (Trend Break)
- **Filter:** Only trade stocks with historical CAGR > 15%
- **Indicators:** SMA 200, Daily Stochastic (10, 3, 3)

## 🏗️ Architecture

```
VolatilityHunter/
├── .env                  # API Keys and configuration
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
├── Dockerfile            # Cloud Run deployment
├── src/
│   ├── config.py         # Environment variables and settings
│   ├── data_loader.py    # Tiingo API integration
│   ├── storage.py        # Local/GCS storage abstraction
│   ├── strategy.py       # Wealth Builder logic
│   └── notifications.py  # Logging and alerts
└── main.py               # Flask server + CLI
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- Tiingo API Key (get free at https://www.tiingo.com/)
- Google Cloud account (for Cloud Run deployment only)

### 2. Installation

```bash
# Clone the repository
cd VolatilityHunter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Edit `.env` file:

```env
TIINGO_KEY=your_tiingo_api_key_here
BUCKET_NAME=your_gcs_bucket_name_here
IS_CLOUD_RUN=False
PORT=8080
```

### 4. Run Locally

**Start Flask Server:**
```bash
python main.py
```
Then visit: http://localhost:8080

**CLI Commands:**
```bash
# Update market data (incremental)
python main.py update

# Full data refresh (2 years)
python main.py update-full

# Scan for trading signals
python main.py scan
```

## 🌐 Flask API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/update` | GET | Update market data (last 7 days) |
| `/update/full` | GET | Full data refresh (2 years) |
| `/scan` | GET | Scan all stocks for signals |
| `/health` | GET | Health check |

### Example Response - `/scan`

```json
{
  "success": true,
  "timestamp": "2026-01-31T16:30:00",
  "summary": {
    "total_stocks": 21,
    "buy_signals": 3,
    "sell_signals": 1,
    "hold_signals": 15,
    "errors": 2,
    "buy_list": ["NVDA", "META", "PLTR"],
    "sell_list": ["TSLA"]
  },
  "signals": {
    "BUY": [
      {
        "ticker": "NVDA",
        "signal": "BUY",
        "reason": "Price above SMA 200 and Stochastic K in sweet spot (45.23)",
        "indicators": {
          "price": 875.50,
          "sma_200": 720.30,
          "stochastic_k": 45.23,
          "cagr": 87.5,
          "date": "2026-01-31"
        }
      }
    ],
    "SELL": [...],
    "HOLD": [...]
  }
}
```

## ☁️ Google Cloud Run Deployment

### 1. Setup GCS Bucket

```bash
# Create bucket for data storage
gsutil mb gs://your-bucket-name

# Set bucket permissions
gsutil iam ch allUsers:objectViewer gs://your-bucket-name
```

### 2. Build and Deploy

```bash
# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Build container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/volatility-hunter

# Deploy to Cloud Run
gcloud run deploy volatility-hunter \
  --image gcr.io/YOUR_PROJECT_ID/volatility-hunter \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars TIINGO_KEY=your_key,BUCKET_NAME=your_bucket,IS_CLOUD_RUN=True
```

### 3. Schedule Updates (Cloud Scheduler)

```bash
# Create a job to update data daily at 9 AM
gcloud scheduler jobs create http daily-update \
  --schedule="0 9 * * *" \
  --uri="https://your-cloud-run-url/update" \
  --http-method=GET
```

## 📈 Tracked Stocks

The bot monitors 21 volatile tech stocks:
- **Semiconductors:** NVDA, AVGO, LRCX, MU, KLAC
- **Cloud/SaaS:** PLTR, ZS, CRWD, CSCO
- **E-commerce:** SHOP, AMZN, MELI
- **Tech Giants:** META, MSFT, GOOGL
- **Consumer:** NFLX, SPOT, DECK, HD
- **EV:** TSLA
- **ETF:** QQQ

## 🔧 Technical Details

### Data Storage

- **Local Mode:** CSVs stored in `data/` folder
- **Cloud Mode:** CSVs stored in Google Cloud Storage bucket

### Indicators Calculation

**SMA 200:**
```python
SMA = Close.rolling(window=200).mean()
```

**Stochastic Oscillator:**
```python
%K = 100 * (Close - Low_min) / (High_max - Low_min)
%K_smooth = %K.rolling(window=3).mean()
%D = %K_smooth.rolling(window=3).mean()
```

**CAGR:**
```python
CAGR = ((End_Price / Start_Price) ^ (1 / Years)) - 1
```

### Strategy Logic

```python
def analyze_stock(df):
    # Calculate indicators
    price = latest['Close']
    sma_200 = latest['SMA_200']
    stoch_k = latest['Stochastic_K']
    cagr = calculate_cagr(df)
    
    # Filter: CAGR must be > 15%
    if cagr < 15:
        return 'HOLD'
    
    # Entry: Price > SMA 200 AND 32 <= Stoch K <= 80
    if price > sma_200 and 32 <= stoch_k <= 80:
        return 'BUY'
    
    # Exit: Price < SMA 200
    if price < sma_200:
        return 'SELL'
    
    return 'HOLD'
```

## 📝 Logging

All activity is logged to:
- Console output
- `volatility_hunter.log` file

Log levels:
- **INFO:** Normal operations, signals
- **WARNING:** Missing data, API issues
- **ERROR:** Failures, exceptions

## 🛡️ Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use environment variables** for API keys
3. **Rotate API keys** regularly
4. **Use GCS IAM** for bucket access control
5. **Enable Cloud Run authentication** for production

## 🧪 Testing Workflow

1. **Initial Setup:**
   ```bash
   python main.py update-full  # Download 2 years of data
   ```

2. **Daily Updates:**
   ```bash
   python main.py update  # Fetch last 7 days
   ```

3. **Scan for Signals:**
   ```bash
   python main.py scan  # Analyze all stocks
   ```

4. **Web Interface:**
   ```bash
   python main.py  # Start server
   # Visit http://localhost:8080
   ```

## 📊 Performance Considerations

- **Batch API Calls:** Fetches 50 tickers per request
- **Incremental Updates:** Only downloads recent data
- **CSV Storage:** Lightweight, version-controllable
- **Async-Ready:** Can be extended with Celery for background tasks

## 🔄 Extending the Bot

### Add New Indicators

Edit `src/strategy.py`:
```python
def calculate_rsi(df, period=14):
    # Your RSI calculation
    pass

def add_indicators(df):
    df['SMA_200'] = calculate_sma(df, 200)
    df['RSI'] = calculate_rsi(df, 14)  # New indicator
    return df
```

### Add New Stocks

Edit `src/config.py`:
```python
STOCK_LIST = [
    'NVDA', 'NFLX', 'YOUR_STOCK', ...
]
```

### Add Email Alerts

Edit `src/notifications.py`:
```python
import smtplib

def send_email_alert(ticker, signal):
    # Your email logic
    pass
```

## 📚 Dependencies

- **pandas:** Data manipulation
- **numpy:** Numerical calculations
- **flask:** Web server
- **gunicorn:** Production WSGI server
- **requests:** HTTP client for Tiingo API
- **python-dotenv:** Environment variable management
- **google-cloud-storage:** GCS integration

## 🐛 Troubleshooting

**Issue:** `TIINGO_KEY not set`
- **Solution:** Add your API key to `.env` file

**Issue:** `No module named 'src'`
- **Solution:** Run from project root directory

**Issue:** `Insufficient data for analysis`
- **Solution:** Run `python main.py update-full` first

**Issue:** GCS permission denied
- **Solution:** Check bucket IAM permissions and service account

## 📄 License

This project is for educational purposes. Use at your own risk. Not financial advice.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open pull request

## ⚠️ Disclaimer

This bot is for educational and research purposes only. Trading stocks involves risk. Past performance does not guarantee future results. Always do your own research and consult with a financial advisor before making investment decisions.

---

**Built with ❤️ for algorithmic traders**
