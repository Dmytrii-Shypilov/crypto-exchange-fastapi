from fastapi import FastAPI
from app.routers.binance_stream import stream_router
from app.routers.auth import auth_router
from app.routers.coins import coins_router
from app.routers.paper_trade import paper_trade_router
from fastapi.middleware.cors import CORSMiddleware

from app.services.binance_client import binance, client

from datetime import datetime
from typing import List


app = FastAPI()

origins = [
    "http://localhost:5173",  # Frontend development server
    # "https://your-production-domain.com",  # Production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific origins
    allow_credentials=True,  # Allow cookies or authentication headers
    # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_methods=["*"],
    allow_headers=["*"],  # Allow all headers
)

def fill_the_limit_order_gpt(hist_trades: List[dict], order: dict):
    my_trades = []
    remaining_amount = float(order['amount'])  # Base currency amount (e.g., BTC)
    remaining_total = float(order['total'])   # Quote currency total (e.g., USDT)

    for trade in hist_trades:
        if order['side'] == 'buy' and not trade['isBuyerMaker']:
            print(f"sell: {trade['price']} buy: {order['price']} match: {float(trade['price']) <= float(order['price'])}")
            if float(trade['price']) <= float(order['price']):
                trade_amount = float(trade['qty'])  # Base currency amount in this trade
                trade_total = float(trade['quoteQty'])  # Quote currency total for this trade
                
                # Check if the remaining amount is fully or partially filled
                if remaining_amount >= trade_amount:
                    print("Partially filling")
                    remaining_amount -= trade_amount
                    remaining_total -= trade_total
                    partially_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade['price'],
                        'amount': trade_amount,
                        'total': trade_total
                    }
                    my_trades.append(partially_filled_trade)
                else:
                    print("Fully filling")
                    partial_trade_total = remaining_amount * float(trade['price'])  # Quote currency for the remaining base amount
                    fully_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade['price'],
                        'amount': remaining_amount,  # Fill only the remaining amount
                        'total': partial_trade_total
                    }
                    my_trades.append(fully_filled_trade)
                    remaining_amount = 0
                    remaining_total = 0
                    break  # Exit as the order is fully filled

        # Stop processing if the order is fully filled
        if remaining_amount <= 0:
            break

    print(f"Remaining amount: {remaining_amount}")
    if remaining_amount > 0:
        # Order is partially filled; update remaining details
        order.update({
            'total': remaining_total,
            'amount': remaining_amount,
            'filled': float(order['amount']) - remaining_amount
        })
    else:
        # Order is fully filled
        order = None

    return order, my_trades


def fill_the_limit_order(hist_trades: List[dict], order: dict):
    my_trades = []
    remaining_amount = float(order['amount'])  # Base currency amount (e.g., BTC)
    remaining_total = float(order['total'])   # Quote currency total (e.g., USDT)

    for trade in hist_trades:
        if order['side'] == 'buy' and not trade['isBuyerMaker']:
            # For buy orders, match trades where the price is less than or equal to the limit price
            if float(trade['price']) <= float(order['price']):
                trade_amount = float(trade['qty'])  # Base currency amount in this trade
                trade_total = float(trade['quoteQty'])  # Quote currency total for this trade

                if remaining_amount >= trade_amount:
                    remaining_amount -= trade_amount
                    remaining_total -= trade_total
                    partially_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade['price'],
                        'amount': trade_amount,
                        'total': trade_total
                    }
                    my_trades.append(partially_filled_trade)
                else:
                    partial_trade_total = remaining_amount * float(trade['price'])
                    fully_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade['price'],
                        'amount': remaining_amount,
                        'total': partial_trade_total
                    }
                    my_trades.append(fully_filled_trade)
                    remaining_amount = 0
                    remaining_total = 0
                    break

        elif order['side'] == 'sell' and trade['isBuyerMaker']:
            print(f"buy: {trade['price']} sell: {order['price']} match: {float(trade['price']) >= float(order['price'])}")
            # For sell orders, match trades where the price is greater than or equal to the limit price
            if float(trade['price']) >= float(order['price']):
                trade_amount = float(trade['qty'])  # Base currency amount in this trade
                trade_total = float(trade['quoteQty'])  # Quote currency total for this trade

                if remaining_amount >= trade_amount:
                    remaining_amount -= trade_amount
                    remaining_total -= trade_total
                    partially_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade['price'],
                        'amount': trade_amount,
                        'total': trade_total
                    }
                    my_trades.append(partially_filled_trade)
                else:
                    partial_trade_total = remaining_amount * float(trade['price'])
                    fully_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade['price'],
                        'amount': remaining_amount,
                        'total': partial_trade_total
                    }
                    my_trades.append(fully_filled_trade)
                    remaining_amount = 0
                    remaining_total = 0
                    break

        # Stop processing if the order is fully filled
        if remaining_amount <= 0:
            break

    if remaining_amount > 0:
        # Order is partially filled; update remaining details
        order.update({
            'total': remaining_total,
            'amount': remaining_amount,
            'filled': float(order['amount']) - remaining_amount
        })
    else:
        # Order is fully filled
        order = None

    return order, my_trades

@app.get('/')
async def hello():
    trades = client.get_historical_trades(symbol='BTCUSDT',limit=500 , fromId= '4332450719')

    my_order_1 = {'orderTime': int(datetime.now().timestamp() * 1000) ,'type': 'limit','pair': 'BTCUSDT', 'side': 'sell', 'price': '98490.00', 'amount': '0.025', 'total': '2462.25'}
    my_order_2 = {'orderTime': int(datetime.now().timestamp() * 1000) ,'type': 'limit','pair': 'BTCUSDT', 'side': 'buy', 'price': '98495.00', 'amount': '0.015', 'total': '1477.08'}
    order, trades= fill_the_limit_order(hist_trades=trades, order=my_order_1)

    result = [order, trades]

    amount = 0
    total= 0
    for trade in trades:
        amount += float(trade['amount'])
        total += float(trade['total'])

    print(f"total:{total} amount:{amount} == t:{my_order_2['total']} a:{my_order_2['amount']}")

    return result
    # trades = binance.get_recent_trades('BTCUSDT')
    # timestamp = trades[-1]['time']
    # id = trades[-1]['id']
    # timestamp_sec = timestamp/ 1000

    # # Convert to a datetime object
    # dt_object = datetime.fromtimestamp(timestamp_sec)

    # # Format the datetime object into a readable string
    # readable_date = dt_object.strftime("%Y-%m-%d %H:%M:%S")
    # return trades, [id, timestamp]




app.include_router(stream_router)
app.include_router(auth_router)
app.include_router(coins_router)
app.include_router(paper_trade_router)
