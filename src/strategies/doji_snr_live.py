import threading
import time
import datetime
import requests
import pandas as pd
from logzero import logger
from src.auth import connect_smartapi
from src.execution import place_order
from src.config import DRY_RUN, POLL_INTERVAL

class LiveDojiSnRBot:
    def __init__(self, symbol, token, exchange, target_pct, trailing_step_pct, qty=25, doji_range_pct=0.15, snr_tolerance_pct=0.2):
        self.symbol = symbol
        self.token = token
        self.exchange = exchange
        
        # Strategy configs
        self.target_pct = target_pct / 100.0
        self.trailing_step_pct = trailing_step_pct / 100.0
        self.doji_range_pct = doji_range_pct  # Max body/range ratio to be a doji
        self.snr_tolerance_pct = snr_tolerance_pct / 100.0 # Tolerance to S&R line
        self.qty = qty
        
        self.running = False
        self.smart_api = None
        self.status = "Initializing..."
        self.logs = []
        
        # S&R Levels
        self.pivots = {} # PP, R1, S1, R2, S2
        
        # Entry Triggers
        self.trigger_mode = None # "BUY" or "SELL" or None
        self.doji_high = None
        self.doji_low = None
        
        # Position tracking
        self.position = {"side": None, "entry_price": 0.0, "qty": 0}
        self.current_sl = 0.0
        self.max_profit_pct = 0.0
        
        self.trade_symbol = None
        self.trade_token = None
        self.scrip_master = None

    def _log(self, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        logger.info(formatted)
        self.logs.append(formatted)
        if len(self.logs) > 50:
            self.logs.pop(0)

    def start(self):
        if self.running: return
        self.running = True
        self.status = "Connecting..."
        self.logs = []
        self._log("Starting Doji S&R Bot...")
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="DojiBot")
        self.thread.start()

    def stop(self):
        self._log("Stopping bot...")
        self.running = False
        self.status = "Stopped."

    def _fetch_pivots(self):
        # Fetch S&R using previous day's Daily Candle
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(days=1)
        # Using a broader date range to ensure we get exactly 1 previous trading session minimum
        start_dt = (now - datetime.timedelta(days=5)).strftime("%Y-%m-%d 00:00")
        end_dt = yesterday.strftime("%Y-%m-%d 23:59")
        
        params = {
            "exchange": "NSE", 
            "tradingsymbol": "Nifty 50", 
            "symboltoken": "99926000",
            "interval": "ONE_DAY",
            "fromdate": start_dt,
            "todate": end_dt,
        }
        res = self.smart_api.getCandleData(params)
        if res and res.get('data') and len(res['data']) > 0:
            prev_candle = res['data'][-1] # Last available day
            high = float(prev_candle[2])
            low = float(prev_candle[3])
            close = float(prev_candle[4])
            
            pp = (high + low + close) / 3
            r1 = (2 * pp) - low
            s1 = (2 * pp) - high
            r2 = pp + (high - low)
            s2 = pp - (high - low)
            
            self.pivots = {"PP": pp, "R1": r1, "S1": s1, "R2": r2, "S2": s2}
            self._log(f"Daily S&R levels formulated -> S2:{s2:.2f} S1:{s1:.2f} PP:{pp:.2f} R1:{r1:.2f} R2:{r2:.2f}")
            return True
        return False

    def _check_doji_near_snr(self, candle):
        o, h, l, c = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
        # 1. Is it a small Doji?
        c_range = h - l
        if c_range == 0: return False
        body = abs(o - c)
        
        if body / c_range <= self.doji_range_pct:
            # 2. Is it near Support or Resistance?
            for level_name, price in self.pivots.items():
                # Checking if High/Low touches or comes within X% of the level
                if abs(h - price)/price < self.snr_tolerance_pct or abs(l - price)/price < self.snr_tolerance_pct:
                    is_resistance = level_name in ["R1", "R2", "PP"]
                    
                    if level_name in ["S1", "S2"]:
                        self._log(f"Doji detected near SUPPORT ({level_name}). Setting Trigger = BUY above {h:.2f}. SL at {l:.2f}.")
                        self.trigger_mode = "BUY"
                        self.doji_high = h
                        self.doji_low = l
                        return True
                    elif level_name in ["R1", "R2", "PP"]:
                        self._log(f"Doji detected near RESISTANCE ({level_name}). Setting Trigger = SELL below {l:.2f}. SL at {h:.2f}.")
                        self.trigger_mode = "SELL"
                        self.doji_high = h
                        self.doji_low = l
                        return True
        return False

    def _run_loop(self):
        self.smart_api = connect_smartapi()
        if not self.smart_api:
            self.status = "API Connection Failed"
            self.running = False
            return
            
        self.status = "Loading Master Data..."
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            data = requests.get(url).json()
            df = pd.DataFrame(data)
            nfo = df[(df['exch_seg'] == 'NFO') & (df['name'] == 'NIFTY') & (df['instrumenttype'] == 'OPTIDX')]
            nfo = nfo[nfo['expiry'] != ""]
            nfo['expiry_dt'] = pd.to_datetime(nfo['expiry'], format="%d%b%Y", errors='coerce')
            self.scrip_master = nfo.dropna(subset=['expiry_dt'])
            if not self.scrip_master.empty:
                self.scrip_master = self.scrip_master[self.scrip_master['expiry_dt'] == self.scrip_master['expiry_dt'].min()]
        except Exception as e:
            self._log(f"Failed loading master: {e}")
            self.running = False
            return
            
        # Initialize Pivots
        if not self._fetch_pivots():
            self._log("Could not fetch daily candle for S&R pivot generation. Exiting.")
            self.status = "Failed (Pivots)"
            self.running = False
            return

        self.status = "Running: Scanning 5-Min Candles..."
        self._log("Fully Initialized. Scanning 5-Min Candles for S&R Dojis...")
        
        last_candle_time = None

        while self.running:
            now = datetime.datetime.now()
            
            # --- 1. Awaiting Trigger: Look for Dojis every 5-min ---
            if self.position['qty'] == 0 and not self.trigger_mode:
                if now.minute % 5 == 1: # Poll shortly after 5 min close
                    try:
                        params = {
                            "exchange": "NSE", 
                            "tradingsymbol": "Nifty 50", 
                            "symboltoken": "99926000",
                            "interval": "FIVE_MINUTE",
                            "fromdate": (now - datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M"),
                            "todate": now.strftime("%Y-%m-%d %H:%M"),
                        }
                        res = self.smart_api.getCandleData(params)
                        if res and res.get('data') and len(res['data']) >= 2:
                            prev_candle = res['data'][-2]
                            c_time = prev_candle[0] # timestamp
                            if c_time != last_candle_time:
                                last_candle_time = c_time
                                self._check_doji_near_snr(prev_candle)
                    except Exception as e:
                        pass
                        
            # --- 2. Arm Trigger: Wait for Breakout/Breakdown ---
            if self.position['qty'] == 0 and self.trigger_mode:
                try:
                    ltp_res = self.smart_api.ltpData(self.exchange, self.symbol, self.token)
                    if ltp_res and ltp_res.get('status'):
                        ltp = float(ltp_res['data']['ltp'])
                        
                        execute_entry = False
                        opt_type = None
                        
                        if self.trigger_mode == "BUY" and ltp > self.doji_high:
                            execute_entry = True
                            opt_type = "CE"
                            self._log(f"Breakout of S&R Doji High at {ltp}! Going LONG (CE).")
                        elif self.trigger_mode == "SELL" and ltp < self.doji_low:
                            execute_entry = True
                            opt_type = "PE"
                            self._log(f"Breakdown of S&R Doji Low at {ltp}! Going SHORT (PE).")
                            
                        if execute_entry:
                            atm_strike = round(ltp / 50) * 50
                            strike_str = f"{atm_strike}00.000000"
                            opt_df = self.scrip_master[
                                (self.scrip_master['strike'] == strike_str) & 
                                (self.scrip_master['symbol'].str.endswith(opt_type))
                            ]
                            
                            if not opt_df.empty:
                                self.trade_symbol = opt_df.iloc[0]['symbol']
                                self.trade_token = opt_df.iloc[0]['token']
                                
                                o_res = self.smart_api.ltpData(self.exchange, self.trade_symbol, self.trade_token)
                                if o_res and o_res.get('status'):
                                    opt_ltp = float(o_res['data']['ltp'])
                                    order_id = place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "BUY", opt_ltp, self.qty)
                                    if order_id:
                                        self.position = {"side": "BUY", "entry_price": opt_ltp, "qty": self.qty}
                                        underlying_sl_dist_pct = abs(ltp - (self.doji_low if self.trigger_mode == "BUY" else self.doji_high)) / ltp
                                        self.current_sl = opt_ltp * (1.0 - underlying_sl_dist_pct)
                                        self.max_profit_pct = 0.0
                                        self._log(f"Entry Set! Underlying SL is at ({self.doji_low if self.trigger_mode == 'BUY' else self.doji_high}). Option SL Premium: {self.current_sl:.2f}")
                                        self.trigger_mode = None
                                        self.status = "In Position"
                                    else:
                                        self._log("Order placement failed.")
                                        self.trigger_mode = None
                except Exception as e:
                    self._log(f"Error checking LTP: {e}")
                    
            # --- 3. Manage Position ---
            if self.position['qty'] > 0:
                try:
                    opt_res = self.smart_api.ltpData(self.exchange, self.trade_symbol, self.trade_token)
                    if opt_res and opt_res.get('status'):
                        opt_ltp = float(opt_res['data']['ltp'])
                        entry = self.position['entry_price']
                        
                        if opt_ltp >= entry * (1.0 + self.target_pct):
                            self._log(f"TARGET HIT at {opt_ltp}. Exiting Position.")
                            place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "SELL", opt_ltp, self.qty)
                            self.position['qty'] = 0
                            self.status = "Running: Scanning 5-Min Candles..."
                        elif opt_ltp <= self.current_sl:
                            self._log(f"STOP LOSS HIT at {opt_ltp}. Exiting Position.")
                            place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "SELL", opt_ltp, self.qty)
                            self.position['qty'] = 0
                            self.status = "Running: Scanning 5-Min Candles..."
                            
                except Exception as e:
                    pass

            if now.hour >= 15 and now.minute >= 10:
                self._log("Market close reached. Stopping.")
                if self.position['qty'] > 0:
                    place_order(self.smart_api, self.trade_symbol, self.trade_token, self.exchange, "SELL", 0, self.qty)
                self.running = False
                self.status = "Stopped"
                break
                
            time.sleep(POLL_INTERVAL)
