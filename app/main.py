from fastapi import FastAPI
from app.routers.binance_stream import stream_router
from app.routers.auth import auth_router
from app.routers.coins import coins_router
from app.routers.paper_trade import paper_trade_router
from fastapi.middleware.cors import CORSMiddleware

from app.services.binance_client import binance, client, trades_retriver

from datetime import datetime, timedelta
from typing import List
from decimal import Decimal


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


from datetime import datetime
from typing import List

def fill_the_limit_order(hist_trades: List[dict], order: dict):
    my_trades = []
    remaining_amount = Decimal(order['amount'])  # Base currency amount (e.g., BTC)
    remaining_total = Decimal(order['total'])   # Quote currency total (e.g., USDT)
    
    # Ensure trades are sorted once by price before filtering
    sorted_trades = sorted(hist_trades, key=lambda x: float(x['price']), reverse=(order['side'] == 'sell'))
    
    if order['side'] == 'buy':
        if float(sorted_trades[0]['price']) <= float(order['price']):
            # Filter trades where isBuyerMaker is False and price <= order's price
            filtered_trades = [trade for trade in sorted_trades if not trade['isBuyerMaker'] and float(trade['price']) <= float(order['price'])]
        else:
            # If the lowest price in sorted trades is higher than the order price, no matches
            return order, my_trades
    
    # Handle 'sell' orders
    elif order['side'] == 'sell':
        if float(sorted_trades[-1]['price']) >= float(order['price']):
            # Filter trades where isBuyerMaker is True and price >= order's price
            filtered_trades = [trade for trade in sorted_trades if trade['isBuyerMaker'] and float(trade['price']) >= float(order['price'])]
        else:
            # If the highest price in sorted trades is lower than the order price, no matches
            return order, my_trades

    # If there are no matching trades, return the original order
    if not filtered_trades:
        return order, my_trades
 
    # Loop through filtered trades to fill the order
    for trade in filtered_trades:
        trade_price = Decimal(trade['price']) # Round price to 2 decimal places for precision
        trade_amount = Decimal(trade['qty'])  # Round qty to 6 decimal places for precision
        trade_total = Decimal(trade['quoteQty']) # Round quoteQty to 2 decimal places
        print(remaining_amount,remaining_total)
        if order['side'] == 'buy' and not trade['isBuyerMaker']:
            if remaining_amount >= trade_amount:
                remaining_amount -= trade_amount
                remaining_total -= trade_total
                partially_filled_trade = {
                    'orderTime': order['orderTime'],
                    'pair': order['pair'],
                    'type': order['type'],
                    'side': order['side'],
                    'executed': int(datetime.now().timestamp() * 1000),
                    'price': trade_price,
                    'amount': trade_amount,
                    'total': trade_total
                }
                my_trades.append(partially_filled_trade)
            else:
                partial_trade_total = remaining_amount * trade_price
                fully_filled_trade = {
                    'orderTime': order['orderTime'],
                    'pair': order['pair'],
                    'type': order['type'],
                    'side': order['side'],
                    'executed': int(datetime.now().timestamp() * 1000),
                    'price': trade_price,
                    'amount': remaining_amount,
                    'total': partial_trade_total
                }
                my_trades.append(fully_filled_trade)
                remaining_amount = 0
                remaining_total = 0
                print(remaining_amount, remaining_total)
                # print(trade['price'], order['price'], order['side'], fully_filled_trade)
                break

        elif order['side'] == 'sell' and trade['isBuyerMaker']:
            if remaining_amount >= trade_amount:
                remaining_amount -= trade_amount
                remaining_total -= trade_total
                partially_filled_trade = {
                    'orderTime': order['orderTime'],
                    'pair': order['pair'],
                    'type': order['type'],
                    'side': order['side'],
                    'executed': int(datetime.now().timestamp() * 1000),
                    'price': trade_price,
                    'amount': trade_amount,
                    'total': trade_total
                }
                my_trades.append(partially_filled_trade)
            
            else:
                partial_trade_total = remaining_amount * trade_price
                fully_filled_trade = {
                    'orderTime': order['orderTime'],
                    'pair': order['pair'],
                    'type': order['type'],
                    'side': order['side'],
                    'executed': int(datetime.now().timestamp() * 1000),
                    'price': trade_price,
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

    # After processing, if there is remaining amount, the order is partially filled
    if remaining_amount > 0:
        order.update({
            'total': remaining_total,
            'amount': remaining_amount,
            'filled': float(order['amount']) - remaining_amount,
            'latestTradeId': filtered_trades[-1]['id']
        })
    else:
        # Order is fully filled, return None
        order = None

    return order, my_trades




@app.get('/')
async def hello():
   
    price= 98472
    my_order_2 = {'orderTime': int(datetime.now().timestamp() * 1000) ,'type': 'limit','pair': 'BTCUSDT', 'side': 'buy', 'price': '98495.00', 'amount': '0.215', 'total': '21176.425'}
    # trades = trades_retriver.get_historical_trades_batch(symbol='BTCUSDT', startTime=int((datetime.now() - timedelta(hours=10)).timestamp() * 1000), endTime = int(datetime.now().timestamp() * 1000))
    last_id = '4332450816'
    it = 35
    while it >0:
        trades = client.get_historical_trades(symbol='BTCUSDT',limit=500 , fromId= last_id)
        last_id = trades[-1]['id']
        # it -=1
        order, trades = fill_the_limit_order(order=my_order_2, hist_trades=trades)
        if not order:
             it=0
    return {'order': my_order_2, 'trades': trades}
    

    # trades =client.get_my_trades(symbol='BTCUSDT', startTime=int((datetime.now() - timedelta(hours=10)).timestamp() * 1000), endTime = int(datetime.now().timestamp() * 1000))
    
    # my_order_1 = {'orderTime': int(datetime.now().timestamp() * 1000) ,'type': 'limit','pair': 'BTCUSDT', 'side': 'sell', 'price': '98490.00', 'amount': '0.025', 'total': '2462.25'}
    # my_order_2 = {'orderTime': int(datetime.now().timestamp() * 1000) ,'type': 'limit','pair': 'BTCUSDT', 'side': 'buy', 'price': '98495.00', 'amount': '0.015', 'total': '1477.08'}

    # symbol = 'BTCUSDT'
    # interval = client.KLINE_INTERVAL_1HOUR
    # time_from = int((datetime.now() - timedelta(hours=10)).timestamp() * 1000)
    # # [0] open time
    # # [2] high price
    # # [3] low price

    # # The HIGH price should be ≥ SELL order price. Low price is irrelevant here
    # # The LOW price of the Kline must be ≤ BUY order price. The high price is irrelevant for this condition.

    # def conv_to_date(timestamp: str):
    #     ts_in_s = int(timestamp)/1000
    #     dt_object = datetime.fromtimestamp(ts_in_s)
    #     formatted_date_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
    #     return formatted_date_time
    
    # # Order of klines is sorted according to the open/close time
    # prices_list = client.get_klines(symbol=symbol, interval=interval, startTime=time_from)
    # filtered = [kline for kline in prices_list if float(kline[3]) <= float(my_order_2['price'])]

    
    # timings= [{'open': conv_to_date(kline[0]) , 'close': conv_to_date(kline[6])} for kline in filtered]
    # # return {'1st': prices_list[0], 'last': prices_list[-1]}

    # return timings
    # last_id = '4332450719'
    # it = 35
    # while it >0:
    #     trades = client.get_historical_trades(symbol='BTCUSDT',limit=500 , fromId= last_id)
    #     last_id = trades[-1]['id']
    #     print(last_id)
    #     # it -=1
    #     print(len(trades))
    
    # order, trades= fill_the_limit_order(hist_trades=trades, order=my_order_1)

    # result = [order, trades]

    # amount = 0
    # total= 0
    # for trade in trades:
    #     amount += float(trade['amount'])
    #     total += float(trade['total'])

    # print(f"total:{total} amount:{amount} == t:{my_order_2['total']} a:{my_order_2['amount']}")

    # return result


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
