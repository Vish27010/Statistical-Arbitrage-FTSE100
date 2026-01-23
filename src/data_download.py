import yfinance as yf
import pandas as pd
import os

# 1. Define your universe (The 'Top-Down' selection)
# These are liquid FTSE 100 tickers
tickers = [
    'SHEL.L', 'BP.L',       # Energy
    'HSBA.L', 'BARC.L',     # Banking
    'AZN.L', 'GSK.L',       # Pharma
    'RIO.L', 'GLEN.L',      # Mining
    'ULVR.L', 'TSCO.L'      # Consumer Goods
]

def download_and_save_data(ticker_list, start="2022-01-01", end="2025-12-31"):
    print(f"Starting data download for {len(ticker_list)} tickers...")
    
    # Download 'Adjusted Close' prices
    # Adjusted Close accounts for dividends and stock splits—crucial for Quants
    data = yf.download(ticker_list, start=start, end=end)['Adj Close']
    
    # Drop any rows with missing data (NaNs)
    data = data.dropna()
    
    # Create the path to your /data folder
    # This works regardless of whether you're on Mac or Windows
    save_path = os.path.join('data', 'ftse_prices.csv')
    
    # Save as CSV
    data.to_csv(save_path)
    print(f"Success! Data saved to: {save_path}")
    print(f"Dataset shape: {data.shape}")

if __name__ == "__main__":
    download_and_save_data(tickers)