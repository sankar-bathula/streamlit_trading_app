import backtrader as bt
from datetime import time, datetime

class Nifty5MinORB(bt.Strategy):
    """
    5-Minute Opening Range Breakout Strategy for Nifty Futures.
    Captures the High/Low of the first few 5-min candles (e.g., 09:15-09:20),
    and trades the breakout with an intraday square-off.
    """
    params = (
        ('orb_start', time(9, 15)),
        ('orb_end', time(9, 20)),
        ('exit_time', time(15, 10)),     # Square off at 3:10 PM
        ('stop_loss_pct', 0.005),        # 0.5% default stop loss
        ('target_pct', 0.015),           # 1.5% default target
        ('print_log', True),             # Enable/disable logging
    )
    
    def __init__(self):
        self.orb_high = None
        self.orb_low = None
        self.orb_formed = False
        
        # Keep track of active order and execution price
        self.order = None
        self.buyprice = None
        self.buycomm = None

    def log(self, txt, dt=None):
        if self.params.print_log:
            dt = dt or self.data.datetime.datetime(0)
            print(f'{dt.strftime("%Y-%m-%d %H:%M:%S")} | {txt}')

    def next(self):
        # Current time of the bar
        current_time = self.data.datetime.time(0)
        current_date = self.data.datetime.date(0)
        
        # Ensure we only process data within standard market hours or relevant periods
        if current_time < self.params.orb_start:
            return

        # 1. Reset ORB tracking logic at the start of a new session
        if current_time == self.params.orb_start:
            self.orb_high = self.data.high[0]
            self.orb_low = self.data.low[0]
            self.orb_formed = False
            
        # 2. Form ORB between orb_start and orb_end
        if getattr(self, 'orb_high', None) is not None and not self.orb_formed:
            if current_time <= self.params.orb_end:
                if self.data.high[0] > self.orb_high:
                    self.orb_high = self.data.high[0]
                if self.data.low[0] < self.orb_low:
                    self.orb_low = self.data.low[0]
                
                # Check if we reached the end of the ORB window
                if current_time >= self.params.orb_end:
                    self.orb_formed = True
                    self.log(f'ORB FORMED -> High: {self.orb_high}, Low: {self.orb_low}')

        # 3. Intraday Square-off
        if current_time >= self.params.exit_time:
            if self.position:
                self.log(f'INTRADAY SQUARE-OFF TRIGGERED -> Closing Position at {self.data.close[0]}')
                self.close()
            return
            
        # 4. Entry logic (only if ORB is formed, we have no active position, and before exit time)
        if self.orb_formed and not self.position and current_time < self.params.exit_time:
            # Avoid duplicate orders
            if self.order:
                return
                
            # Break above ORB High
            if self.data.close[0] > self.orb_high:
                self.log(f'BUY CREATE -> Breakout above ORB High: {self.orb_high}')
                self.order = self.buy()
                
            # Break below ORB Low
            elif self.data.close[0] < self.orb_low:
                self.log(f'SELL CREATE -> Breakout below ORB Low: {self.orb_low}')
                self.order = self.sell()
                
        # 5. Stop Loss & Target Management
        if self.position:
            # Current value and PnL monitoring based on entry price
            if self.position.size > 0: # Long
                if self.data.close[0] <= self.buyprice * (1.0 - self.params.stop_loss_pct):
                    self.log('LONG STOP LOSS HIT -> Closing')
                    self.close()
                elif self.data.close[0] >= self.buyprice * (1.0 + self.params.target_pct):
                    self.log('LONG TARGET HIT -> Closing')
                    self.close()
            elif self.position.size < 0: # Short
                if self.data.close[0] >= self.buyprice * (1.0 + self.params.stop_loss_pct):
                    self.log('SHORT STOP LOSS HIT -> Closing')
                    self.close()
                elif self.data.close[0] <= self.buyprice * (1.0 - self.params.target_pct):
                    self.log('SHORT TARGET HIT -> Closing')
                    self.close()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Clear active order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')
