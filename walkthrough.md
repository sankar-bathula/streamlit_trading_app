# Doji Support & Resistance Strategy Walkthrough

The Streamlit trading application now supports an automated **Doji S&R Breakout** trading strategy natively!

## Functional Overview
When selected from the "Live Trading" page, the newly integrated [LiveDojiSnRBot](file:///d:/Dev_GoogleAntigravity/finance/streamlit_trading_app/src/strategies/doji_snr_live.py#11-271) strategy will:
1. **Compute Pivots**: Connect to Angel One SmartAPI and pull the previous day's Daily candle to compute precise **Pivot Points (PP, R1, S1, R2, S2)**.
2. **Scan for S&R Dojis**: Query 5-minute candles to find the formation of "Small Doji" candlesticks (where the body is less than `<doji_range_pct>` of the total High-Low spread). It then checks if the Doji touched any Support or Resistance pivot line (within `<snr_tolerance_pct>`).
3. **Set Triggers**:
    * If a Doji is found on Support (S1/S2), it arms a `BUY` trigger. If price breaches the Doji's High, it enters a long position (CE Option). The Stop Loss is automatically calculated to sit exactly at the Doji's Low.
    * If a Doji is found on Resistance (R1/R2/PP), it arms a `SELL` trigger. If price pierces the Doji's Low, it initiates a short position (PE Option). The Stop Loss is anchored at the Doji's High.

## User Interface Additions
On the `Live Trading` Tab of your Streamlit app:
- Introduced a **Select Strategy Algorithm** radio toggle.
- When toggling to **Doji S&R Breakout**, strategy-specific input fields automatically swap out the ORB inputs. You can customize the `Max Doji Body/Range Ratio` and `S&R Tolerance %`.
- The real-time Bot Status panel will log specifically when it finds a Pivot Doji ('Waiting for Trigger' mode), logging the Highs and Lows of the triggering candlestick.

## Executable Steps
1. Make sure you load the app locally: `streamlit run d:\Dev_GoogleAntigravity\finance\streamlit_trading_app\app.py`
2. Connect the Angel One backend on the *Dashboard*.
3. Go to *Live Trading*, pick **Doji S&R Breakout**, set your configurations, and click **Start Bot**!

Listed directory streamlit_trading_app
Listed directory src
Edited creds.py

I have restored/created a template for your [creds.py](cci:7://file:///d:/Dev_GoogleAntigravity/finance/streamlit_trading_app/creds.py:0:0-0:0) file in the root of your project: [creds.py](file:///d:/Dev_GoogleAntigravity/finance/streamlit_trading_app/creds.py).

Please make sure to fill in the following:
*   **`api_key`**: From your Angel One Developer Portal.
*   **`client_code`**: Your Angel One Client ID (e.g., A12345).
*   **`client_pin`**: Your 4-digit MPIN.
*   **`totp_code`**: **CRITICAL** - This must be your **32-character TOTP Seed Key** (the secret used to generate codes), **NOT** the 6-digit dynamic number from your authenticator app.

Once you save those details in the file, your "Connect SmartAPI" button in the Streamlit app should work correctly.