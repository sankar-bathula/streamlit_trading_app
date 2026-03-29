import streamlit as st
import pandas as pd
import json
import os
import sys

# Add current dir to path to find src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.auth import connect_smartapi
from src.backtester import run_backtest
from src.live_breakout import LiveBreakoutBot
from src.strategies.doji_snr_live import LiveDojiSnRBot
import time

st.set_page_config(page_title="Algorithmic Trading Dashboard", layout="wide", page_icon="📈")

st.title("Algorithmic Trading Dashboard")

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Watchlist", "Backtesting", "Live Trading", "Settings"])

if "smart_api" not in st.session_state:
    st.session_state.smart_api = None

if "live_bot" not in st.session_state:
    st.session_state.live_bot = None

if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

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
            
elif page == "Watchlist":
    st.subheader("Live Market Watchlist")
    st.write("Add Index, Stocks, or Options to track their Last Traded Price (LTP).")
    
    with st.form("add_watchlist_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            wl_exchange = st.selectbox("Exchange", ["NSE", "NFO", "BSE", "MCX"])
        with col2:
            wl_symbol = st.text_input("Trading Symbol", placeholder="e.g. Nifty 50")
        with col3:
            wl_token = st.text_input("Token", placeholder="e.g. 99926000")
            
        submitted = st.form_submit_button("Add to Watchlist")
        if submitted:
            if wl_symbol and wl_token:
                # Check for duplicates
                exists = any(item['token'] == wl_token for item in st.session_state.watchlist)
                if not exists:
                    st.session_state.watchlist.append({
                        "exchange": wl_exchange,
                        "symbol": wl_symbol,
                        "token": wl_token
                    })
                    st.success(f"Added {wl_symbol} to watchlist.")
                else:
                    st.warning("Symbol is already in watchlist.")
            else:
                st.error("Please provide both Trading Symbol and Token.")
                
    st.markdown("---")
    
    if len(st.session_state.watchlist) > 0:
        if st.session_state.smart_api:
            # Refresh button
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.write("### Current Prices")
            with col_b:
                if st.button("🔄 Refresh Prices"):
                    pass # Streamlit natively refreshes on button click
            
            # Fetch LTPs
            data = []
            for item in st.session_state.watchlist:
                ltp = "Error"
                try:
                    res = st.session_state.smart_api.ltpData(item["exchange"], item["symbol"], item["token"])
                    if res and res.get('status'):
                        ltp = res['data']['ltp']
                    else:
                        ltp = "N/A"
                except Exception as e:
                    ltp = "Failed"
                    
                data.append({
                    "Exchange": item["exchange"],
                    "Symbol": item["symbol"],
                    "Token": item["token"],
                    "LTP": float(ltp) if isinstance(ltp, str) and ltp.replace('.', '', 1).isdigit() else ltp
                })
                
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            # Removal
            st.write("Remove from Watchlist:")
            remove_options = [""] + [f"{i['symbol']} ({i['token']})" for i in st.session_state.watchlist]
            remove_token = st.selectbox("Select Symbol to Remove", options=remove_options)
            if st.button("Remove Selected"):
                if remove_token:
                    # extract token
                    tok = remove_token.split("(")[-1].strip(")")
                    st.session_state.watchlist = [i for i in st.session_state.watchlist if i['token'] != tok]
                    st.rerun()
        else:
            st.warning("Please connect SmartAPI from the Dashboard to view live prices.")
            df = pd.DataFrame(st.session_state.watchlist)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
    else:
        st.info("Watchlist is empty. Add symbols above to track prices.")
            
elif page == "Backtesting":
    st.subheader("Backtrader Engine: Nifty 5-Min ORB")
    
    st.write("Configure the Opening Range Breakout parameters:")
    col1, col2 = st.columns(2)
    with col1:
        orb_start_str = st.text_input("ORB Start Time (HH:MM)", value="09:15")
        orb_end_str = st.text_input("ORB End Time (HH:MM)", value="09:20")
        exit_time_str = st.text_input("Intraday Exit Time (HH:MM)", value="15:10")
        
    with col2:
        stop_loss_pct = st.number_input("Stop Loss %", value=0.5, step=0.1) / 100.0
        target_pct = st.number_input("Target %", value=1.5, step=0.1) / 100.0
        cash = st.number_input("Starting Capital", value=100000)
        
    if st.button("Run Nifty 5-Min Backtest"):
        with st.spinner("Downloading ^NSEI 5-min data and running backtest..."):
            try:
                # Run the backtest using our backtester engine
                cerebro, result = run_backtest(cash=cash, print_log=False)
                final_val = cerebro.broker.getvalue()
                
                st.success("Backtest Completed!")
                st.metric("Final Portfolio Value", f"₹ {final_val:.2f}", f"₹ {final_val - cash:.2f}")
                
                # Plot the result using matplotlib
                import matplotlib
                matplotlib.use('Agg') # Ensure Streamlit compatibility
                
                # Capture the plot
                fig = cerebro.plot(style='candlestick', barup='green', bardown='red')[0][0]
                st.pyplot(fig)
                
            except Exception as e:
                st.error(f"Error during backtesting: {e}")

elif page == "Live Trading":
    st.subheader("Live Market Execution")
    strategy_choice = st.radio("Select Strategy Algorithm", ["5-Min ORB", "Doji S&R Breakout"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        trade_symbol = st.text_input("Underlying Symbol", value="NIFTY27FEB26FUT")
        trade_token = st.text_input("Underlying Token", value="57072")
        trade_exchange = st.text_input("Exchange (usually NFO)", value="NFO")
        
    with col2:
        target_pct = st.number_input("Target Profit %", value=1.5, step=0.1)
        qty = st.number_input("Quantity (Lots/Shares)", value=25, step=25)
        
        if strategy_choice == "5-Min ORB":
            stop_loss_pct = st.number_input("Initial Stop Loss %", value=0.5, step=0.1)
            trailing_sl_step = st.number_input("Trailing SL Step %", value=0.2, step=0.1)
        else:
            st.info("Stop Loss is dynamically set to the high/low of the Doji candlestick.")
            doji_range_pct = st.number_input("Max Doji Body/Range Ratio", value=0.15, step=0.01)
            snr_tolerance_pct = st.number_input("S&R Tolerance %", value=0.2, step=0.1)
        
    st.markdown("---")
    res_col1, res_col2 = st.columns([1, 2])
    
    with res_col1:
        st.write("Bot Control")
        if st.session_state.live_bot and st.session_state.live_bot.running:
            if st.button("Stop Live Bot", type="secondary"):
                st.session_state.live_bot.stop()
                st.success("Stop signal sent.")
        else:
            if st.button("Start Live Bot", type="primary"):
                if strategy_choice == "5-Min ORB":
                    bot = LiveBreakoutBot(trade_symbol, trade_token, trade_exchange, 
                                          target_pct, stop_loss_pct, trailing_sl_step,
                                          qty=qty)
                else:
                    bot = LiveDojiSnRBot(trade_symbol, trade_token, trade_exchange, 
                                         target_pct, 0.2, qty=qty, 
                                         doji_range_pct=doji_range_pct, 
                                         snr_tolerance_pct=snr_tolerance_pct)
                st.session_state.live_bot = bot
                bot.start()
                st.success(f"{strategy_choice} Bot started in background!")
                
        # Status
        bot = st.session_state.live_bot
        if bot:
            status_color = "green" if bot.running else "red"
            st.markdown(f"**Bot Class:** `{bot.__class__.__name__}`")
            st.markdown(f"**Status:** :{status_color}[{bot.status}]")
            
            if strategy_choice == "5-Min ORB" and hasattr(bot, 'orb_high'):
                st.write(f"**ORB High:** {bot.orb_high}")
                st.write(f"**ORB Low:** {bot.orb_low}")
            elif hasattr(bot, 'trigger_mode'):
                st.write(f"**S&R Status:** {bot.trigger_mode or 'Waiting for Doji'}")
                if bot.trigger_mode:
                    st.write(f"**Doji Range:** {bot.doji_low} - {bot.doji_high}")
            
            st.write(f"**Position:** {bot.position['side']} ({bot.position['qty']})")
            if bot.position['qty'] > 0:
                st.write(f"**Entry Price:** {bot.position['entry_price']}")
                st.write(f"**Current SL:** {bot.current_sl:.2f}")

    with res_col2:
        st.write("Bot Logs")
        if st.button("Refresh Logs"):
            pass # Streamlit natively refreshes on button click
            
        logs_box = st.container(height=300)
        bot = st.session_state.live_bot
        if bot and len(bot.logs) > 0:
            for l in reversed(bot.logs):
                logs_box.text(l)
        else:
            logs_box.info("No logs generated yet.")

elif page == "Settings":
    st.subheader("Configuration")
    st.write("Modify your settings and thresholds here.")
    st.info("Settings panel under construction.")
