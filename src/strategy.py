import pandas as pd
import ta

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical indicators using pandas and the `ta` library.
    """
    # Example: MACD
    df['macd'] = ta.trend.macd_diff(df['close'])
    
    # Example: RSI
    df['rsi'] = ta.momentum.rsi(df['close'])
    
    return df

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate BUY/SELL signals based on computed indicators.
    """
    df = compute_indicators(df)
    
    # Placeholder logic
    df['signal'] = 0
    # Buy when RSI < 30 and MACD is positive
    df.loc[(df['rsi'] < 30) & (df['macd'] > 0), 'signal'] = 1
    # Sell when RSI > 70 and MACD is negative
    df.loc[(df['rsi'] > 70) & (df['macd'] < 0), 'signal'] = -1
    
    return df
