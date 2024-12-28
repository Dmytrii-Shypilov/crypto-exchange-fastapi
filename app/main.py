from datetime import datetime
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


def fill_the_limit_order(order: dict):
    print(order)
    state = {
        'side': order['side'],
        'searchExhausted': False,
        'fillComplete': False,
        'latestTradeId': order['latestTradeId'],
        'myTrades': [],
        'remAmount': Decimal(order['amount']),
        'remTotal': Decimal(order['total']),
        'balance': {
            'orderTotal': Decimal(order['total']),
            'orderAmount': Decimal(order['amount']),
            'tradesTotal':Decimal('0'),
            'tradesAmount': Decimal('0'),
        }
    }

    while not state['fillComplete'] and not state['searchExhausted']:
       
        hist_trades = client.get_historical_trades(
            symbol='BTCUSDT', fromId=state['latestTradeId'], limit=1000)
        
        # Exit loop if no more trades
        if not hist_trades:
            state['searchExhausted'] = True
            break

        # Sort trades by price (ascending for buy, descending for sell)
        sorted_trades = sorted(
            hist_trades, 
            key=lambda x: Decimal(x['price']), 
            reverse=(order['side'] == 'sell')
        )

        # Filter trades based on side and price
        if order['side'] == 'buy':
            filtered_trades = [
                trade for trade in sorted_trades 
                if not trade['isBuyerMaker'] and Decimal(trade['price']) <= Decimal(order['price'])
            ]
        else:  # sell
            filtered_trades = [
                trade for trade in sorted_trades 
                if trade['isBuyerMaker'] and Decimal(trade['price']) >= Decimal(order['price'])
            ]

        # Update latestTradeId to the highest ID in current batch
        state['latestTradeId'] = int(hist_trades[-1]['id']) + 1
        print(f'Id: {state['latestTradeId']} histTrLen: {len(hist_trades)} filterdeLen: {len(filtered_trades)}' )
        # Skip to next iteration if no matching trades
        if not filtered_trades:
            continue

        # Process filtered trades
        for trade in filtered_trades:
            trade_price = Decimal(trade['price'])
            trade_amount = Decimal(trade['qty'])
            trade_total = trade_price * trade_amount

            if state['remAmount'] >= trade_amount:
                # Full trade match
               
                state['remAmount'] -= trade_amount
                state['remTotal'] -= trade_total
                state['myTrades'].append({
                    'pair': order['pair'],
                    'orderTime': order['orderTime'],
                    'type': order['type'],
                    'side': order['side'],
                    'executed': int(datetime.now().timestamp() * 1000),
                    'price': trade_price,
                    'amount': trade_amount,
                    'total': trade_total,
                })
                state['balance']['tradesTotal'] += trade_total
                state['balance']['tradesAmount'] += trade_amount
            else:
                # Partial trade match
                partial_trade_total = state['remAmount'] * trade_price
                state['myTrades'].append({
                    'pair': order['pair'],
                    'orderTime': order['orderTime'],
                    'type': order['type'],
                    'side': order['side'],
                    'executed': int(datetime.now().timestamp() * 1000),
                    'price': trade_price,
                    'amount': state['remAmount'],
                    'total': partial_trade_total,
                })
                state['balance']['tradesAmount'] += state['remAmount']
                state['balance']['tradesTotal'] += partial_trade_total
                state['remAmount'] = Decimal(0)
                state['remTotal'] = Decimal(0)
                state['fillComplete'] = True
                 
                break

        # Stop processing if fully filled
        if state['fillComplete']:
            break
    state['balance'].update({'quoteDifference': state['balance']['tradesTotal'] - state['balance']['orderTotal']})
    return  state


@app.get('/')
async def hello():
    print('Hello')
     # price= 98472
    lat_id = '4332450816'
    price = Decimal('120300')
    base = Decimal('0.23')
    tot_quote = price * base
    my_order_2 = {'orderTime': int(datetime.now().timestamp() * 1000), 'type': 'limit', 'pair': 'BTCUSDT',
                    'side': 'sell', 'price': price, 'amount': base, 'total': tot_quote, 'latestTradeId': lat_id}
  
    state = fill_the_limit_order(order=my_order_2)
    total = 0
    amount = 0
   

    for trade in state['myTrades']:
        total+= trade['total']
        amount+= trade['amount']
    # del state['myTrades']
    comparison = {'ordT': my_order_2['total'], 'ordA': my_order_2['amount'], 'finT':total, 'finA': amount}
    return state, comparison
        # while it >0:
        #     trades = client.get_historical_trades(symbol='BTCUSDT',limit=500 , fromId= last_id)
        #     last_id = trades[-1]['id']
        #     # it -=1
        #     order, trades = fill_the_limit_order(order=my_order_2, hist_trades=trades)
        #     print(trades[0])
        #     if not order:
        #          it=0
        # return {'order': my_order_2, 'trades': trades}

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
