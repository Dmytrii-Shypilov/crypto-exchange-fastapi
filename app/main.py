from fastapi import FastAPI
from app.routers.binance_stream import stream_router

from app.services.binance_client import binance


app = FastAPI()


@app.get('/')
async def hello():
    order_book = binance.get_order_book_info('BTCUSDT')
    coins_trades = binance.get_recent_trades('BTCUSDT')
    coins_info = binance.get_traded_pair_info('BTCUSDT')
    
    
   
    # print(type(order_book['bids'][0][0])) - > str
    return {'coinsInfo': coins_info,
            # 'orderBook': order_book,
            'trades': coins_trades 
            }

app.include_router(stream_router)
