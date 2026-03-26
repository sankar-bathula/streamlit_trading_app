import streamlit as st
import pandas as pd
import json
import os
import sys

# Add current dir to path to find src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.auth import connect_smartapi

st.set_page_config(page_title="Algorithmic Trading Dashboard", layout="wide", page_icon="📈")

st.title("Algorithmic Trading Dashboard")

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Backtesting", "Settings"])

if "smart_api" not in st.session_state:
    st.session_state.smart_api = None

if page == "Dashboard":
    st.subheader("Live Market Status")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("Broker Connection:")
        if st.button("Connect SmartAPI"):
            api = connect_smartapi()
            if api:
                st.session_state.smart_api = api
                st.success("Connected successfully!")
            else:
                st.error("Connection failed. Check credentials.")
                
        if st.session_state.smart_api:
            st.success("SmartAPI is Active")
        else:
            st.warning("SmartAPI not connected")

    with col2:
        st.write("Recent Signals/Alerts:")
        alerts_file = "logs/alerts.json"
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        if not os.path.exists(alerts_file):
            with open(alerts_file, "w") as f:
                json.dump([], f)
                
        try:
            with open(alerts_file, "r") as f:
                alerts = json.load(f)
            if alerts:
                df = pd.DataFrame(alerts)
                st.dataframe(df.tail(10))
            else:
                st.info("No recent alerts.")
        except Exception as e:
            st.error(f"Could not load alerts: {e}")
            
elif page == "Backtesting":
    st.subheader("Backtrader Engine")
    st.write("Select a strategy and click 'Run' to see backtest results.")
    if st.button("Run Backtest"):
        st.info("Backtesting engine execution triggered.")
        # Future: call src.backtester

elif page == "Settings":
    st.subheader("Configuration")
    st.write("Modify your settings and thresholds here.")
    st.info("Settings panel under construction.")
