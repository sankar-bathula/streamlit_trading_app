import backtrader as bt
from datetime import datetime
import pandas as pd
import yfinance as yf
from src.strategies.nifty_5m_breakout import Nifty5MinORB

def download_sample_data():
    """Download sample Nifty 50 data from yfinance (5-minute interval)."""
    # Note: Yahoo Finance restricts 5-min data to last 60 days
    ticker = "^NSEI"
    try:
        df = yf.download(ticker, period="30d", interval="5m")
        # Rename columns to lowercase for backtrader
        df.columns = [c[0].lower() for c in df.columns]
        # Backtrader requires Open, High, Low, Close, Volume
        if 'adj close' in df.columns:
            df = df.drop(columns=['adj close'])
        # Drop rows with NaN
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"Error downloading sample data: {e}")
        return pd.DataFrame()

def run_backtest(df=None, strategy_class=Nifty5MinORB, cash=100000.0, print_log=False):
    """
    Run backtest using a pandas dataframe (e.g. from SmartAPI or CSV)
    """
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class, print_log=print_log)
    
    if df is None or df.empty:
        print("No dataframe provided, downloading sample Nifty50 5-min data...")
        df = download_sample_data()
        if df.empty:
            raise ValueError("Failed to obtain data for backtesting.")

    # Convert df to Backtrader data feed
    # df must have datetime index and open, high, low, close, volume columns
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Start balance
    cerebro.broker.setcash(cash)
    
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    result = cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    print(f'Final Portfolio Value: {final_value:.2f}')
    
    # Return cerebro and result for Streamlit integration (e.g., plotting)
    return cerebro, result
