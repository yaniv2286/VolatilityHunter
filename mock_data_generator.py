#!/usr/bin/env python3
"""
Mock Data Generator for Quick Testing
Generates realistic test data without API calls
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json

class MockDataGenerator:
    """Generate mock market data for testing."""
    
    def __init__(self, seed=42):
        """Initialize with random seed for reproducible tests."""
        np.random.seed(seed)
    
    def generate_stock_data(self, ticker, days=250, start_price=100.0, trend=0.001):
        """Generate realistic stock price data."""
        
        # Generate dates
        start_date = datetime.now() - timedelta(days=days)
        dates = pd.date_range(start_date, periods=days, freq='D')
        
        # Generate price series with trend and volatility
        returns = np.random.normal(trend, 0.02, days)  # Daily returns
        prices = start_price * np.cumprod(1 + returns)
        
        # Generate OHLCV data
        data = []
        for i, price in enumerate(prices):
            # Add some intraday variation
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = price * (1 + np.random.normal(0, 0.005))
            
            # Ensure OHLC relationships
            high = max(high, open_price, price)
            low = min(low, open_price, price)
            
            volume = np.random.randint(1000000, 10000000)
            
            data.append({
                'date': dates[i],
                'Open': round(open_price, 2),
                'High': round(high, 2),
                'Low': round(low, 2),
                'Close': round(price, 2),
                'Volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_bullish_stock(self, ticker, days=250):
        """Generate stock in uptrend (BUY signal)."""
        return self.generate_stock_data(ticker, days, start_price=100.0, trend=0.002)
    
    def generate_bearish_stock(self, ticker, days=250):
        """Generate stock in downtrend (SELL signal)."""
        return self.generate_stock_data(ticker, days, start_price=100.0, trend=-0.002)
    
    def generate_sideways_stock(self, ticker, days=250):
        """Generate stock in range (HOLD signal)."""
        return self.generate_stock_data(ticker, days, start_price=100.0, trend=0.0001)
    
    def generate_test_portfolio(self):
        """Generate test portfolio state."""
        return {
            'cash': 70000.0,
            'positions': {
                'BULL1': {
                    'shares': 50.0,
                    'entry_price': 100.0,
                    'entry_date': '2026-01-01',
                    'quality_score': 18.5
                },
                'BULL2': {
                    'shares': 25.0,
                    'entry_price': 200.0,
                    'entry_date': '2026-01-01',
                    'quality_score': 15.2
                }
            },
            'trade_history': [
                {
                    'type': 'BUY',
                    'ticker': 'BULL1',
                    'shares': 50.0,
                    'entry_price': 100.0,
                    'entry_date': '2026-01-01',
                    'cost': 5000.0,
                    'quality_score': 18.5
                },
                {
                    'type': 'BUY',
                    'ticker': 'BULL2',
                    'shares': 25.0,
                    'entry_price': 200.0,
                    'entry_date': '2026-01-01',
                    'cost': 5000.0,
                    'quality_score': 15.2
                }
            ]
        }
    
    def generate_test_universe(self, size=10):
        """Generate small test universe of stocks."""
        tickers = [f'STOCK{i:02d}' for i in range(1, size + 1)]
        test_data = {}
        
        # Mix of different stock types
        for i, ticker in enumerate(tickers):
            if i < size // 3:
                # Bullish stocks
                test_data[ticker] = self.generate_bullish_stock(ticker)
            elif i < 2 * size // 3:
                # Bearish stocks
                test_data[ticker] = self.generate_bearish_stock(ticker)
            else:
                # Sideways stocks
                test_data[ticker] = self.generate_sideways_stock(ticker)
        
        return test_data
    
    def save_mock_data(self, output_dir="test_data"):
        """Save mock data to files for testing."""
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate test universe
        test_data = self.generate_test_universe(20)
        
        # Save each stock to CSV
        for ticker, df in test_data.items():
            filename = f"{ticker}_1d_full_{datetime.now().strftime('%Y%m%d')}.csv"
            filepath = os.path.join(output_dir, filename)
            df.to_csv(filepath, index=False)
        
        # Save test portfolio
        portfolio_file = os.path.join(output_dir, "test_portfolio.json")
        with open(portfolio_file, 'w') as f:
            json.dump(self.generate_test_portfolio(), f, indent=2)
        
        print(f"Mock data saved to {output_dir}/")
        print(f"Generated {len(test_data)} stock files")
        print(f"Portfolio file: test_portfolio.json")
        
        return output_dir

def create_mock_environment():
    """Create complete mock testing environment."""
    
    print("Creating mock testing environment...")
    
    generator = MockDataGenerator()
    
    # Generate and save mock data
    data_dir = generator.save_mock_data()
    
    # Create mock config for testing
    mock_config = {
        "DATA_SOURCE": "local",
        "LOCAL_DATA_DIR": data_dir,
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": 587,
        "SENDER_EMAIL": "test@example.com",
        "RECIPIENT_EMAIL": "test@example.com"
    }
    
    config_file = os.path.join(data_dir, "test_config.json")
    with open(config_file, 'w') as f:
        json.dump(mock_config, f, indent=2)
    
    print(f"Mock config: {config_file}")
    print("\nMock environment ready for testing!")
    print(f"Data directory: {data_dir}")
    
    return data_dir

if __name__ == "__main__":
    create_mock_environment()
