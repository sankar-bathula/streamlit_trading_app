# Streamlit Algorithmic Trading App

## Prerequisites
1. Open `creds.py` and replace the placeholder strings with your actual AngleOne SmartAPI credentials.
2. (Optional) Provide your Telegram Bot Token and Chat ID for alerts.

## Setup Env & Install Dependencies
```bash
pip install -r requirements.txt
```

## Running the Application
The system is divided into two parts: the UI Dashboard and the Webhook Listener.

### 1. Start the Streamlit Dashboard
```bash
streamlit run app.py
```
This will open the web interface in your default browser.

### 2. Start the TradingView Webhook Server
```bash
uvicorn webhook_server:app --reload --port 8000
```

## Future Upgrades
- **FinRL**: Code stubs are present in `src/finrl_agent.py`
-  for training and calling DRL models.
- **Backtrader**: Configured in `src/backtester.py`. Connect to historical OHLCV data to run full backtest simulations on Streamlit.


Scrip Master Download: As soon as you click "Start Live Bot" in the Streamlit app, it downloads Angel One's master list of symbols.
Breakout Detection: The bot monitors the NIFTY index (using the Future/Spot ticker you provide) until it breaks out of the 5-min ORB envelope.
Dynamic ATM Calculation: The moment a breakout (BUY) or breakdown (SELL) is detected, the bot calculates the current At-The-Money (ATM) strike price (rounding the LTP to the nearest 50 points, e.g., 22500).
Option Target Acquisition: It immediately searches the Scrip Master to find the nearest-expiry Call (CE) or Put (PE) option corresponding to that exact strike.
Execution & Trailing Stop Loss: The bot buys that Option contract. From that point forward, the Auto Step-Up Trailing Stop Loss mathematically tracks the Option's Premium Price, not the Index price, ensuring your Target % and Stop Loss % ratios are totally accurate to the capital you have put on the table.
This API server listens on port 8000 for POST requests (`http://localhost:8000/webhook`) from TradingView alerts and logs them to `logs/alerts.json`, which the Streamlit Dashboard reads and displays.
