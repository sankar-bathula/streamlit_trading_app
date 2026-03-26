import backtrader as bt
from datetime import datetime

class StreamlitStrategy(bt.Strategy):
    """
    A Backtrader Strategy that can be parameterized via UI.
    """
    params = (
        ('rsi_period', 14),
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

    def next(self):
        if not self.position:
            if self.rsi < self.params.rsi_oversold:
                self.buy(size=1)
        else:
            if self.rsi > self.params.rsi_overbought:
                self.sell(size=1)

def run_backtest(df):
    """
    Run backtest using a pandas dataframe (e.g. from SmartAPI or CSV)
    """
    cerebro = bt.Cerebro()
    cerebro.addstrategy(StreamlitStrategy)
    
    # Convert df to Backtrader data feed
    # df must have datetime index and open, high, low, close, volume columns
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Start balance
    cerebro.broker.setcash(100000.0)
    
    result = cerebro.run()
    
    # We could capture the plot and return it to Streamlit,
    # or return analytics for the Streamlit GUI.
    return cerebro, result
