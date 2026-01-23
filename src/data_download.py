import yfinance as yf
import pandas as pd
import os
import time

tickers = ['SHEL.L', 'BP.L', 'HSBA.L', 'BARC.L', 'AZN.L', 'GSK.L', 'RIO.L', 'GLEN.L', 'ULVR.L', 'TSCO.L']

def download_robustly(ticker_list):
    all_data = {}
    
    for ticker in ticker_list:
        print(f"Downloading {ticker}...")
        try:
            # We download and immediately 'flatten' the data
            df = yf.download(ticker, start="2022-01-01", end="2026-01-01", 
                             progress=False, auto_adjust=True)
            
            if not df.empty:
                # FIX: We use .squeeze() to turn a 1-column DataFrame into a Series
                # and we ensure we only take the 'Close' column regardless of Multi-Index
                if 'Close' in df.columns:
                    all_data[ticker] = df['Close'].squeeze()
                else:
                    # This handles the case where the header is ('Ticker', 'Close')
                    all_data[ticker] = df.iloc[:, 0] 
            else:
                print(f"Warning: {ticker} returned no data.")
                
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"Error downloading {ticker}: {e}")

    # 1. Create the DataFrame
    # 2. Force the index to be Datetime (sometimes Yahoo sends it as objects)
    final_df = pd.DataFrame(all_data)
    final_df.index = pd.to_datetime(final_df.index)
    
    # Drop rows where everything is NaN
    final_df = final_df.dropna(how='all') 

    # Save to CSV
    save_path = os.path.join('data', 'ftse_prices.csv')
    final_df.to_csv(save_path)
    
    print("\n--- Final Report ---")
    print(f"Successfully saved {len(final_df.columns)} tickers.")
    print(f"Dataset Shape: {final_df.shape}")
    
    if not final_df.empty:
        print("\nFirst 5 rows of data:")
        print(final_df.head())

if __name__ == "__main__":
    # Ensure the data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
        
    download_robustly(tickers)