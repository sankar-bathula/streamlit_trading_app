from SmartApi import SmartConnect
from logzero import logger
from src.config import DRY_RUN

def place_order(smart_api: SmartConnect, symbol: str, token: str, exchange: str, side: str, price: float, qty: int) -> str | None:
    """
    Place an intraday MIS market/limit order.
    """
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would place {side} {qty}x {symbol} @ ~{price}")
        return "DRY_RUN_ID"

    params = {
        "variety": "NORMAL",
        "tradingsymbol": symbol,
        "symboltoken": token,
        "transactiontype": side,
        "exchange": exchange,
        "ordertype": "MARKET" if price == 0 else "LIMIT",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": str(price),
        "squareoff": "0",
        "stoploss": "0",
        "quantity": str(qty),
    }

    try:
        response = smart_api.placeOrder(params)
        if response and response.get("status"):
            order_id = response["data"]["orderid"]
            logger.info(f"Order placed successfully: {order_id}")
            return order_id
        else:
            logger.error(f"Order placement failed: {response}")
            return None
    except Exception as e:
        logger.error(f"Exception during order placement: {e}")
        return None
