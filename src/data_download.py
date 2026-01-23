import yfinance as yf
import pandas as pd
import os
import time

# 1. Define your universe (The 'Top-Down' selection)
# These are liquid FTSE 100 tickers
tickers = [
    'SHEL.L', 'BP.L',       # Energy
    'HSBA.L', 'BARC.L',     # Banking
    'AZN.L', 'GSK.L',       # Pharma
    'RIO.L', 'GLEN.L',      # Mining
    'ULVR.L', 'TSCO.L'      # Consumer Goods
]

def download_robustly(ticker_list):
    all_data = {}
    
    for ticker in ticker_list:
        print(f"Downloading {ticker}...")
        try:
            # Download individual ticker
            # we use period='5y' to get plenty of data for our 3-year window
            df = yf.download(ticker, start="2022-01-01", end="2026-01-01", progress=False)
            
            if not df.empty:
                # We only want the 'Adj Close' column
                all_data[ticker] = df['Adj Close']
            else:
                print(f"Warning: {ticker} returned no data.")
                
            # Small pause to avoid being rate-limited by Yahoo
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"Error downloading {ticker}: {e}")

    # Combine all individual series into one big DataFrame
    final_df = pd.DataFrame(all_data)
    
    # Now we drop only rows where EVERY stock is missing (rare)
    # or handle specific missing values later
    final_df = final_df.dropna(how='all') 

    # Save to CSV
    save_path = os.path.join('data', 'ftse_prices.csv')
    final_df.to_csv(save_path)
    
    print("\n--- Final Report ---")
    print(f"Successfully saved {len(final_df.columns)} tickers.")
    print(f"Dataset Shape: {final_df.shape}")
    print(f"Missing values per ticker:\n{final_df.isnull().sum()}")

if __name__ == "__main__":
    download_robustly(tickers)