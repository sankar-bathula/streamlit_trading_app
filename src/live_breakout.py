import threading
import time
import datetime
import requests
import pandas as pd
from logzero import logger
from src.auth import connect_smartapi
from src.execution import place_order
from src.config import DRY_RUN, POLL_INTERVAL

class LiveBreakoutBot:
    def __init__(self, symbol, token, exchange, target_pct, stop_loss_pct, trailing_step_pct, qty=25, paper_trade=True):
        self.symbol = symbol
        self.token = token
        self.exchange = exchange
        self.paper_trade = paper_trade
        
        # Convert percentages to decimals
        self.target_pct = target_pct / 100.0
        self.stop_loss_pct = stop_loss_pct / 100.0
        self.trailing_step_pct = trailing_step_pct / 100.0
        self.qty = qty
        
        self.running = False
        self.smart_api = None
        
        self.status = "Initializing..."
        self.logs = []
        
        self.orb_high = None
        self.orb_low = None
        
        # Position tracking
        self.position = {"side": None, "entry_price": 0.0, "qty": 0}
        self.max_profit_pct = 0.0  # Tracks highest profit for trailing SL
        self.current_sl = 0.0      # Absolute price of current SL
        self.trade_symbol = None   # dynamically updated to Option symbol
        self.trade_token = None    # dynamically updated Option token
        self.scrip_master = None
        
    def _log(self, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        logger.info(formatted)
        self.logs.append(formatted)
        if len(self.logs) > 50:
            self.logs.pop(0)  # Keep last 50 logs for UI
            
    def start(self):
        if self.running:
            return
        self.running = True
        self.status = "Connecting to SmartAPI..."
        self.logs = [] # Clear logs on new start
        self._log(f"Starting Live Trader. Monitoring {self.symbol} to trade Dynamic ATM Options...")
        
        # Start background thread
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="LiveTrader")
        self.thread.start()

    def stop(self):
        self._log("Stopping bot. Sending halt signal...")
        self.running = False
        self.status = "Stopped."
        
    def _get_strike_params(self, symbol):
        """Determine scrip master name and strike interval based on symbol."""
        s = symbol.upper()
        if "BANKNIFTY" in s:
            return "BANKNIFTY", 100
        elif "FINNIFTY" in s:
            return "FINNIFTY", 50
        elif "NIFTY" in s:
            return "NIFTY", 50
        else:
            return "NIFTY", 50 # Default

    def _run_loop(self):
        self.smart_api = connect_smartapi()
        if not self.smart_api:
            self.status = "API Connection Failed!"
            self._log("Failed to connect to SmartAPI. Bot stopped.")
            self.running = False
            return
            
        name_filter, strike_step = self._get_strike_params(self.symbol)
        
        self.status = "Downloading Scrip Master..."
        self._log(f"Downloading OpenAPIScripMaster for {name_filter} ATM selection...")
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            data = requests.get(url).json()
            df = pd.DataFrame(data)
            
            # Use dynamic name filter
            nfo = df[(df['exch_seg'] == 'NFO') & (df['name'] == name_filter) & (df['instrumenttype'] == 'OPTIDX')]
            nfo = nfo[nfo['expiry'] != ""]
            nfo['expiry_dt'] = pd.to_datetime(nfo['expiry'], format="%d%b%Y", errors='coerce')
            self.scrip_master = nfo.dropna(subset=['expiry_dt'])
            
            if self.scrip_master.empty:
                self._log(f"Error: No options found in Scrip Master for {name_filter}")
                self.running = False
                return
                
            nearest_expiry = self.scrip_master['expiry_dt'].min()
            self._log(f"Nearest Expiry for Options: {nearest_expiry}")
            # Keep only nearest expiry
            self.scrip_master = self.scrip_master[self.scrip_master['expiry_dt'] == nearest_expiry]
            
        except Exception as e:
            self._log(f"Error downloading Scrip Master: {e}")
            self.running = False
            return
            
        self.status = "Running"
        self._log(f"SmartAPI Connected! Waiting for ORB Data...")
        
        while self.running:
            now = datetime.datetime.now()
            
            # 1. Fetch ORB if not set and Time is past 09:20
            if not self.orb_high and now.hour >= 9 and now.minute >= 20:
                self._log(f"Fetching 5-min ORB candle data for {self.symbol} (09:15 - 09:20)...")
                try:
                    # Using the actual symbol and token provided in __init__
                    params = {
                        "exchange": self.exchange, 
                        "tradingsymbol": self.symbol, 
                        "symboltoken": self.token,
                        "interval": "FIVE_MINUTE",
                        "fromdate": now.strftime("%Y-%m-%d 09:15"),
                        "todate": now.strftime("%Y-%m-%d 09:20"),
                    }
                    res = self.smart_api.getCandleData(params)
                    if res and res.get('status') and res.get('data') and len(res['data']) > 0:
                        candle = res['data'][0] # first candle 
                        self.orb_high = float(candle[2]) # High
                        self.orb_low = float(candle[3])  # Low
                        self._log(f"ORB Set -> High: {self.orb_high:.2f}, Low: {self.orb_low:.2f}")
                    else:
                        self._log(f"Warning: No candle data found for {self.symbol} ORB yet.")
                except Exception as e:
                    self._log(f"Error fetching ORB data: {e}")
                    
            # 2. Main Logic once ORB is set
            if self.orb_high:
                try:
                    # Fetch Live Price of the Future
                    ltp_res = self.smart_api.ltpData(self.exchange, self.symbol, self.token)
                    if ltp_res and ltp_res.get('status'):
                        index_ltp = float(ltp_res['data']['ltp'])
                        
                        # --- Position Management (Tracking Option LTP) ---
                        if self.position['qty'] > 0:
                            opt_res = self.smart_api.ltpData(self.exchange, self.trade_symbol, self.trade_token)
                            if opt_res and opt_res.get('status'):
                                opt_ltp = float(opt_res['data']['ltp'])
                                entry = self.position['entry_price']
                                
                                if self.position['side'] == "BUY":
                                    profit_pct = (opt_ltp - entry) / entry
                                    
                                    # Trailing SL Setup
                                    if profit_pct > self.max_profit_pct:
                                        self.max_profit_pct = profit_pct
                                        steps = int(self.max_profit_pct / self.trailing_step_pct)
                                        if steps > 0:
                                            new_sl = entry * (1.0 - self.stop_loss_pct + (steps * self.trailing_step_pct))
                                            if new_sl > self.current_sl:
                                                self.current_sl = new_sl
                                                self._log(f"Trailing SL Stepped Up to: {self.current_sl:.2f}")

                                    # Targets and Stops Check
                                    if opt_ltp >= entry * (1.0 + self.target_pct):
                                        self._log(f"TARGET HIT at {opt_ltp}. Exiting BUY.")
                                        place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "SELL", opt_ltp, self.qty, paper_trade=self.paper_trade)
                                        self.position['qty'] = 0
                                    elif opt_ltp <= self.current_sl:
                                        self._log(f"STOP LOSS HIT at {opt_ltp}. Exiting BUY.")
                                        place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "SELL", opt_ltp, self.qty, paper_trade=self.paper_trade)
                                        self.position['qty'] = 0
                                        
                                elif self.position['side'] == "SELL":
                                    # Wait, we are buying options, so if we wanted to short the market, we BUY a PE.
                                    # Therefore the position side is STILL a BUY of the option.
                                    # We don't short options because of margin. 
                                    profit_pct = (opt_ltp - entry) / entry
                                    
                                    # Trailing SL Setup
                                    if profit_pct > self.max_profit_pct:
                                        self.max_profit_pct = profit_pct
                                        steps = int(self.max_profit_pct / self.trailing_step_pct)
                                        if steps > 0:
                                            new_sl = entry * (1.0 - self.stop_loss_pct + (steps * self.trailing_step_pct))
                                            if new_sl > self.current_sl:
                                                self.current_sl = new_sl
                                                self._log(f"Trailing SL Stepped Up to: {self.current_sl:.2f}")
                                                
                                    # Targets and Stops Check
                                    if opt_ltp >= entry * (1.0 + self.target_pct):
                                        self._log(f"TARGET HIT at {opt_ltp}. Exiting PE BUY.")
                                        place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "SELL", opt_ltp, self.qty, paper_trade=self.paper_trade)
                                        self.position['qty'] = 0
                                    elif opt_ltp <= self.current_sl:
                                        self._log(f"STOP LOSS HIT at {opt_ltp}. Exiting PE BUY.")
                                        place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "SELL", opt_ltp, self.qty, paper_trade=self.paper_trade)
                                        self.position['qty'] = 0

                        # --- Entry Logic ---
                        if self.position['qty'] == 0:
                            if index_ltp > self.orb_high or index_ltp < self.orb_low:
                                is_buy = index_ltp > self.orb_high
                                opt_type = "CE" if is_buy else "PE"
                                action_label = "BREAKOUT" if is_buy else "BREAKDOWN"
                                
                                atm_strike = round(index_ltp / strike_step) * strike_step
                                strike_str = f"{atm_strike * 100:.6f}"
                                
                                # Search for the option
                                opt_df = self.scrip_master[
                                    (self.scrip_master['strike'] == strike_str) & 
                                    (self.scrip_master['symbol'].str.endswith(opt_type))
                                ]
                                
                                if not opt_df.empty:
                                    self.trade_symbol = opt_df.iloc[0]['symbol']
                                    self.trade_token = opt_df.iloc[0]['token']
                                    
                                    self._log(f"{action_label}! {self.symbol}: {index_ltp}. ATM Option: {self.trade_symbol} (Strike: {atm_strike})")
                                    
                                    # Get Option Premium Price
                                    opt_res = self.smart_api.ltpData(self.exchange, self.trade_symbol, self.trade_token)
                                    if opt_res and opt_res.get('status'):
                                        opt_ltp = float(opt_res['data']['ltp'])
                                        self._log(f"Option Premium: {opt_ltp}")
                                        
                                        # Execute Trade (We BUY the option either way - CE for Breakout, PE for Breakdown)
                                        order_id = place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "BUY", opt_ltp, self.qty, paper_trade=self.paper_trade)
                                        if order_id:
                                            # We track our trade as a "BUY" in terms of option premium
                                            # regardless if it's CE or PE
                                            side_label = "BUY" if is_buy else "SELL" # logical direction
                                            self.position = {"side": side_label, "entry_price": opt_ltp, "qty": self.qty} # track it logically but mathematically both are bought options
                                            self.current_sl = opt_ltp * (1.0 - self.stop_loss_pct)
                                            self.max_profit_pct = 0.0
                                            self._log(f"Initial SL set at Option Premium: {self.current_sl:.2f}")
                                    else:
                                        self._log("Failed to fetch LTP for the Option.")
                                else:
                                    self._log(f"Warning: Could not find '{opt_type}' option for strike {atm_strike}.")
                
                except Exception as e:
                    self._log(f"Error checking LTP: {e}")
                    
            # 3. Time Check
            if now.hour >= 15 and now.minute >= 10:
                self._log("Market close (3:10 PM) reached. Squaring off and stopping.")
                if self.position['qty'] > 0:
                    # We are always LONG on the option (CE or PE), so square off is a SELL
                    place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "SELL", 0, self.qty, paper_trade=self.paper_trade)
                self.running = False
                self.status = "Stopped (Market Closed)"
                break
                
            time.sleep(POLL_INTERVAL)
