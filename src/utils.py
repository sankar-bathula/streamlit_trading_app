import streamlit as st
import pandas as pd
from datetime import datetime

def get_index_quotes(api):
    """
    Fetches LTP and calculates daily change for Nifty 50, BankNifty, and Sensex.
    Returns a list of dicts with index data.
    """
    indices = [
        {"name": "Nifty 50", "symbol": "Nifty 50", "token": "99926000", "exchange": "NSE"},
        {"name": "BankNifty", "symbol": "Nifty Bank", "token": "99926009", "exchange": "NSE"},
        {"name": "Sensex", "symbol": "SENSEX", "token": "99919000", "exchange": "BSE"}
    ]
    
    results = []
    
    if not api:
        return []

    for index in indices:
        try:
            # Get OHLC to calculate change from previous close
            res = api.getOHLC(index["exchange"], index["symbol"], index["token"])
            if res and res.get('status'):
                data = res['data']
                ltp = float(data.get('ltp', 0))
                close = float(data.get('close', 0))
                
                change = ltp - close
                pct_change = (change / close * 100) if close != 0 else 0
                
                results.append({
                    "name": index["name"],
                    "ltp": ltp,
                    "change": change,
                    "pct_change": pct_change
                })
            else:
                # Fallback to LTP if OHLC fails
                ltp_res = api.ltpData(index["exchange"], index["symbol"], index["token"])
                if ltp_res and ltp_res.get('status'):
                    ltp = float(ltp_res['data'].get('ltp', 0))
                    results.append({
                        "name": index["name"],
                        "ltp": ltp,
                        "change": 0,
                        "pct_change": 0
                    })
        except Exception as e:
            print(f"Error fetching {index['name']}: {e}")
            
    return results

def render_market_row(index_data):
    """
    Renders a row of metrics for the indices.
    """
    if not index_data:
        st.warning("No market data available. Connect SmartAPI to see live indices.")
        return

    cols = st.columns(len(index_data))
    for i, data in enumerate(index_data):
        with cols[i]:
            name = data['name']
            ltp = data['ltp']
            change = data['change']
            pct = data['pct_change']
            
            delta_str = f"{change:+.2f} ({pct:+.2f}%)"
            st.metric(label=name, value=f"{ltp:,.2f}", delta=delta_str)
