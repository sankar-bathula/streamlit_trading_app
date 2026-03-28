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
This API server listens on port 8000 for POST requests (`http://localhost:8000/webhook`) from TradingView alerts and logs them to `logs/alerts.json`, which the Streamlit Dashboard reads and displays.

## Future Upgrades
- **FinRL**: Code stubs are present in `src/finrl_agent.py` for training and calling DRL models.
- **Backtrader**: Configured in `src/backtester.py`. Connect to historical OHLCV data to run full backtest simulations on Streamlit.

git remote add origin https://github.com/sankar-bathula/streamlit_trading_app.git
git branch -M main
git push -u origin main