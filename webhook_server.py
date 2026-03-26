from fastapi import FastAPI, Request
from datetime import datetime
import json
import os

app = FastAPI(title="TradingView Webhook Server")

ALERTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "alerts.json")
os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    """
    Receives alerts from TradingView via POST.
    Expected payload format:
    {
        "symbol": "NIFTY",
        "action": "BUY",
        "price": 22000,
        "message": "MACD crossing up"
    }
    """
    try:
        data = await request.json()
        data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Read existing alerts
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, "r") as f:
                alerts = json.load(f)
        else:
            alerts = []
            
        alerts.append(data)
        
        # Keep only last 100 alerts
        alerts = alerts[-100:]
        
        # Write back
        with open(ALERTS_FILE, "w") as f:
            json.dump(alerts, f, indent=4)
            
        return {"status": "success", "message": "Alert received and logged"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/")
def read_root():
    return {"status": "ok", "message": "TradingView Webhook Server is running"}
