"""
Deep History Data Fetcher for 20-Year Vectorized Backtest
Pulls 20 years of daily data (2004-01-01 to Present) from Tiingo for S&P 500 core universe
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
import time
import json

# Add src to path for imports
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(script_dir)

from src.config import TIINGO_KEY, TIINGO_BASE_URL
from src.notifications import log_info, log_error, log_warning
import tiingo

class DeepHistoryFetcher:
    """Fetch 20 years of historical data for vectorized backtesting"""
    
    def __init__(self, start_date='2004-01-01', end_date=None):
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        self.data_dir = os.path.join(script_dir, 'data')
        self.min_trading_days = 4000  # 20 years ≈ 4000 trading days
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize Tiingo client
        self.tiingo_client = tiingo.TiingoClient(api_key=TIINGO_KEY)
        
        # S&P 500 core universe (top tickers by market cap)
        self.sp500_universe = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", 
            "JNJ", "V", "PG", "UNH", "HD", "MA", "BAC", "XOM", "CVX", "LLY", 
            "ABBV", "PFE", "KO", "PEP", "TMO", "COST", "ABT", "DHR", "MCD",
            "ACN", "VZ", "ADBE", "NFLX", "CRM", "PYPL", "INTC", "CSCO",
            "CMCSA", "AMD", "TXN", "QCOM", "IBM", "AMGN", "GILD", "MDT",
            "ISRG", "BDX", "REGN", "AVGO", "NOW", "MU", "CSX", "NSC", "UNP",
            "KSU", "FDX", "UPS", "LUV", "DAL", "AAL", "UAL", "HA", "ALK",
            "CAT", "DE", "GE", "MMM", "HON", "BA", "RTX", "LMT", "NOC",
            "GD", "COF", "AXP", "BLK", "GS", "MS", "SCHW", "BK", "T",
            "WFC", "C", "BAC", "JPM", "USB", "PNC", "TFC", "KEY", "FITB",
            "STI", "CMA", "ZION", "RF", "HBAN", "WAL", "PFG", "AIG", "MET",
            "PRU", "ALL", "TRV", "CB", "CINF", "AFL", "HIG", "L", "RE",
            "WRB", "MKL", "AON", "AJG", "BRO", "ACGL", "WTW", "HCI", "FAF",
            "RNR", "CNA", "KNSL", "PRA", "FNF", "GTLB", "RHI", "MAN", "KBR",
            "J", "CARR", "OTIS", "CTVA", "DOW", "CC", "FCX", "NEM", "RIO",
            "BHP", "VALE", "X", "CLF", "NUE", "STLD", "TX", "RS", "CRS",
            "ATI", "CMCL", "GOLD", "WPM", "FNV", "RGLD", "SAND", "KL", "AGI",
            "EXK", "EGO", "AU", "GFI", "DRD", "HL", "PAAS", "SVM", "SSRM",
            "TECK", "IAG", "NG", "AEM", "EQX", "CEY", "HMY", "BTG", "KGC",
            "GORO", "MUX", "UGP", "USAP", "URM", "AVTR", "UNF", "HWM", "TGI",
            "HEI", "HEIA", "SPR", "BAH", "LHX", "NOC", "GD", "RTX", "TXT",
            "HII", "CW", "TDY", "TDG", "ERJ", "HEES", "AIR", "MCHP", "ADI",
            "TXN", "INTC", "AMD", "NVDA", "QCOM", "MU", "MRVL", "LRCX", "AMAT",
            "KLAC", "ON", "SWKS", "CRUS", "QRVO", "AVGO", "MPWR", "NXPI", "SYNA",
            "CY", "SMTC", "DIOD", "PLAB", "COHR", "FORM", "MTSI", "SLAB", "POWR",
            "AEHR", "IMCC", "WOLF", "ALGM", "SQNS", "GCTS", "PLTK", "VERI",
            "ICHR", "COHU", "CAMT", "AEIS", "MRCY", "OSIS", "MANH", "TYL",
            "PTC", "ANSS", "CDNS", "SNPS", "MENT", "KEYS", "RNG", "ZS", "NOW",
            "TEAM", "ADSK", "INTU", "CRM", "WDAY", "SAP", "ORCL", "ADP", "PAYX",
            "CTAS", "PAYC", "GLOB", "RHI", "MAN", "KBR", "J", "CARR", "OTIS",
            "CTVA", "DOW", "CC", "FCX", "NEM", "RIO", "BHP", "VALE", "X",
            "CLF", "NUE", "STLD", "TX", "RS", "CRS", "ATI", "CMCL", "GOLD",
            "WPM", "FNV", "RGLD", "SAND", "KL", "AGI", "EXK", "EGO", "AU",
            "GFI", "DRD", "HL", "PAAS", "SVM", "SSRM", "TECK", "IAG", "NG",
            "AEM", "EQX", "CEY", "HMY", "BTG", "KGC", "GORO", "MUX", "UGP",
            "USAP", "URM", "AVTR", "UNF", "HWM", "TGI", "HEI", "HEIA", "SPR",
            "BAH", "LHX", "NOC", "GD", "RTX", "TXT", "HII", "CW", "TDY", "TDG",
            "ERJ", "HEES", "AIR", "MCHP", "ADI", "TXN", "INTC", "AMD", "NVDA",
            "QCOM", "MU", "MRVL", "LRCX", "AMAT", "KLAC", "ON", "SWKS", "CRUS",
            "QRVO", "AVGO", "MPWR", "NXPI", "SYNA", "CY", "SMTC", "DIOD",
            "PLAB", "COHR", "FORM", "MTSI", "SLAB", "POWR", "AEHR", "IMCC",
            "WOLF", "ALGM", "SQNS", "GCTS", "PLTK", "VERI", "ICHR", "COHU",
            "CAMT", "AEIS", "MRCY", "OSIS", "MANH", "TYL", "PTC", "ANSS",
            "CDNS", "SNPS", "MENT", "KEYS", "RNG", "ZS", "NOW", "TEAM", "ADSK",
            "INTU", "CRM", "WDAY", "SAP", "ORCL", "ADP", "PAYX", "CTAS", "PAYC",
            "GLOB", "RHI", "MAN", "KBR", "J", "CARR", "OTIS", "CTVA", "DOW",
            "CC", "FCX", "NEM", "RIO", "BHP", "VALE", "X", "CLF", "NUE", "STLD",
            "TX", "RS", "CRS", "ATI", "CMCL", "GOLD", "WPM", "FNV", "RGLD",
            "SAND", "KL", "AGI", "EXK", "EGO", "AU", "GFI", "DRD", "HL", "PAAS",
            "SVM", "SSRM", "TECK", "IAG", "NG", "AEM", "EQX", "CEY", "HMY",
            "BTG", "KGC", "GORO", "MUX", "UGP", "USAP", "URM", "AVTR", "UNF",
            "HWM", "TGI", "HEI", "HEIA", "SPR", "BAH", "LHX", "NOC", "GD",
            "RTX", "TXT", "HII", "CW", "TDY", "TDG", "ERJ", "HEES", "AIR",
            "MCHP", "ADI", "TXN", "INTC", "AMD", "NVDA", "QCOM", "MU", "MRVL",
            "LRCX", "AMAT", "KLAC", "ON", "SWKS", "CRUS", "QRVO", "AVGO",
            "MPWR", "NXPI", "SYNA", "CY", "SMTC", "DIOD", "PLAB", "COHR",
            "FORM", "MTSI", "SLAB", "POWR", "AEHR", "IMCC", "WOLF", "ALGM",
            "SQNS", "GCTS", "PLTK", "VERI", "ICHR", "COHU", "CAMT", "AEIS",
            "MRCY", "OSIS", "MANH", "TYL", "PTC", "ANSS", "CDNS", "SNPS",
            "MENT", "KEYS", "RNG", "ZS", "NOW", "TEAM", "ADSK", "INTU", "CRM",
            "WDAY", "SAP", "ORCL", "ADP", "PAYX", "CTAS", "PAYC", "GLOB"
        ]
        
        # Rate limiting: Tiingo allows 500 calls/hour
        self.rate_limit_delay = 7.2  # 3600 seconds / 500 calls = 7.2 seconds per call
        
        log_info(f"DeepHistoryFetcher initialized: {len(self.sp500_universe)} tickers, {self.start_date} to {self.end_date}")
    
    def get_existing_files(self):
        """Get list of already downloaded 20yr files"""
        existing_files = []
        for file in os.listdir(self.data_dir):
            if file.endswith('_20yr.parquet'):
                ticker = file.replace('_20yr.parquet', '')
                existing_files.append(ticker)
        return existing_files
    
    def validate_dataframe(self, df, ticker):
        """Validate downloaded DataFrame meets quality standards"""
        if df is None or len(df) == 0:
            return False, "Empty DataFrame"
        
        # Check minimum trading days
        if len(df) < self.min_trading_days:
            return False, f"Insufficient data: {len(df)} < {self.min_trading_days} days"
        
        # Check required columns
        required_cols = ['adjClose', 'adjVolume', 'adjHigh', 'adjLow', 'adjOpen']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        
        # Check for excessive gaps
        date_range = (df.index[-1] - df.index[0]).days
        expected_days = date_range * 5/7  # Approximate trading days
        if len(df) < expected_days * 0.8:  # Allow 20% gap tolerance
            return False, f"Too many gaps: {len(df)} vs expected {expected_days}"
        
        return True, "Valid"
    
    def fetch_ticker_data(self, ticker):
        """Fetch data for a single ticker with error handling"""
        try:
            log_info(f"Fetching {ticker} from {self.start_date} to {self.end_date}")
            
            # Get daily price data
            df = self.tiingo_client.get_dataframe(
                ticker,
                startDate=self.start_date,
                endDate=self.end_date,
                frequency='daily'
            )
            
            if df is None or len(df) == 0:
                log_error(f"No data returned for {ticker}")
                return None
            
            # Validate data quality
            is_valid, message = self.validate_dataframe(df, ticker)
            if not is_valid:
                log_error(f"Data validation failed for {ticker}: {message}")
                return None
            
            log_info(f"Successfully fetched {ticker}: {len(df)} days")
            return df
            
        except Exception as e:
            log_error(f"Error fetching {ticker}: {e}")
            return None
    
    def save_ticker_data(self, df, ticker):
        """Save ticker data to parquet file"""
        try:
            parquet_path = os.path.join(self.data_dir, f"{ticker}_20yr.parquet")
            df.to_parquet(parquet_path)
            log_info(f"Saved {ticker} to {parquet_path}")
            return True
        except Exception as e:
            log_error(f"Error saving {ticker}: {e}")
            return False
    
    def fetch_universe(self, batch_size=50):
        """Fetch data for entire universe with batch processing and resume capability"""
        log_info(f"Starting deep history fetch for {len(self.sp500_universe)} tickers")
        
        # Get existing files to resume
        existing_files = self.get_existing_files()
        log_info(f"Found {len(existing_files)} existing files, resuming...")
        
        # Filter out already downloaded tickers
        pending_tickers = [ticker for ticker in self.sp500_universe if ticker not in existing_files]
        log_info(f"Pending tickers: {len(pending_tickers)}")
        
        if not pending_tickers:
            log_info("All tickers already downloaded!")
            return
        
        # Process in batches
        successful_downloads = 0
        failed_downloads = 0
        
        for i in range(0, len(pending_tickers), batch_size):
            batch = pending_tickers[i:i + batch_size]
            log_info(f"Processing batch {i//batch_size + 1}/{(len(pending_tickers)-1)//batch_size + 1}: {batch}")
            
            for ticker in tqdm(batch, desc=f"Batch {i//batch_size + 1}"):
                try:
                    # Fetch data
                    df = self.fetch_ticker_data(ticker)
                    
                    if df is not None:
                        # Save data
                        if self.save_ticker_data(df, ticker):
                            successful_downloads += 1
                        else:
                            failed_downloads += 1
                    else:
                        failed_downloads += 1
                    
                    # Rate limiting
                    time.sleep(self.rate_limit_delay)
                    
                except KeyboardInterrupt:
                    log_info("Download interrupted by user")
                    return
                except Exception as e:
                    log_error(f"Unexpected error processing {ticker}: {e}")
                    failed_downloads += 1
                    continue
            
            # Batch summary
            log_info(f"Batch {i//batch_size + 1} completed. Success: {successful_downloads}, Failed: {failed_downloads}")
        
        # Final summary
        total_processed = successful_downloads + failed_downloads
        log_info(f"Deep history fetch completed!")
        log_info(f"Total processed: {total_processed}")
        log_info(f"Successful: {successful_downloads}")
        log_info(f"Failed: {failed_downloads}")
        log_info(f"Success rate: {successful_downloads/total_processed*100:.1f}%")
    
    def generate_summary_report(self):
        """Generate summary report of downloaded data"""
        log_info("Generating summary report...")
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'start_date': self.start_date,
            'end_date': self.end_date,
            'universe_size': len(self.sp500_universe),
            'downloaded_files': [],
            'missing_tickers': [],
            'data_quality': {}
        }
        
        # Check downloaded files
        existing_files = self.get_existing_files()
        
        for ticker in self.sp500_universe:
            parquet_path = os.path.join(self.data_dir, f"{ticker}_20yr.parquet")
            
            if ticker in existing_files:
                try:
                    df = pd.read_parquet(parquet_path)
                    summary['downloaded_files'].append({
                        'ticker': ticker,
                        'days': len(df),
                        'start': df.index[0].strftime('%Y-%m-%d'),
                        'end': df.index[-1].strftime('%Y-%m-%d'),
                        'size_mb': os.path.getsize(parquet_path) / (1024*1024)
                    })
                except Exception as e:
                    log_error(f"Error reading {ticker}: {e}")
                    summary['missing_tickers'].append(ticker)
            else:
                summary['missing_tickers'].append(ticker)
        
        # Save summary
        summary_path = os.path.join(self.data_dir, 'deep_history_summary.json')
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        log_info(f"Summary report saved to {summary_path}")
        log_info(f"Downloaded: {len(summary['downloaded_files'])}/{len(self.sp500_universe)} tickers")
        
        return summary


def main():
    """Main execution function"""
    print("="*80)
    print("VolatilityHunter - Deep History Data Fetcher")
    print("20-Year Vectorized Backtest Infrastructure")
    print("="*80)
    
    try:
        # Initialize fetcher
        fetcher = DeepHistoryFetcher(start_date='2004-01-01')
        
        # Fetch universe data
        fetcher.fetch_universe(batch_size=50)
        
        # Generate summary report
        summary = fetcher.generate_summary_report()
        
        print("\n" + "="*80)
        print("DEEP HISTORY FETCH COMPLETED")
        print(f"Downloaded: {len(summary['downloaded_files'])}/{len(fetcher.sp500_universe)} tickers")
        print(f"Success Rate: {len(summary['downloaded_files'])/len(fetcher.sp500_universe)*100:.1f}%")
        print("="*80)
        
    except Exception as e:
        log_error(f"Fatal error in main: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
