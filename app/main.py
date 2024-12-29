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

def fill_the_limit_order( order: dict):
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

        # price_match = self.is_price_relevant(order=order)
        # if not price_match['isRelevant']:
        #     state['latestTradeId'] = price_match['latestTradeId']
        #     state['searchExhausted'] =True
        #     return state

        while not state['fillComplete'] and not state['searchExhausted']:
        
            hist_trades = client.get_historical_trades(
                symbol=order['pair'], fromId=state['latestTradeId'], limit=1000)
            # Exit loop if no more trades
            if not len(hist_trades) :
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
                    # PArtial trade match
                
                    state['remAmount'] -= trade_amount
                    state['remTotal'] = Decimal(order['price']) * state['remAmount']
                    state['myTrades'].append({
                        'pair': order['pair'],
                        'orderTime': order['orderTime'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': order['price'],
                        'amount': trade_amount,
                        'total': Decimal(order['price']) * trade_amount,
                    })
                    state['balance']['tradesTotal'] += Decimal(order['price']) * trade_amount
                    state['balance']['tradesAmount'] += trade_amount
                else:
                    # Full trade match if remAmount(order amount) < Trade Amount
                    partial_trade_total = state['remAmount'] * Decimal(order['price'])
                    state['myTrades'].append({
                        'pair': order['pair'],
                        'orderTime': order['orderTime'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': order['price'],
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
        # if order partially filled and trades are exxhausted => remAmount and remTotal are present in state 
        # to update the order amount an total fields in cache
        return  state


@app.get('/')
async def hello():
    print('Hello')
     # price= 98472
    lat_id = client.get_recent_trades(symbol='BTCUSDT')[0]['id']
    price = Decimal('95200')
    base = Decimal('0.23')
    tot_quote = price * base
    my_order_2 = {'orderTime': int((datetime.now() - timedelta(hours=10)).timestamp() * 1000), 'type': 'limit', 'pair': 'BTCUSDT',
                    'side': 'buy', 'price': price, 'amount': base, 'total': tot_quote, 'latestTradeId': lat_id}
    result = fill_the_limit_order(order=my_order_2)
    return result
    

app.include_router(stream_router)
app.include_router(auth_router)
app.include_router(coins_router)
app.include_router(paper_trade_router)
