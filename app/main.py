from fastapi import FastAPI
from app.routers.binance_stream import stream_router
from app.routers.auth import auth_router
from app.routers.coins import coins_router
from fastapi.middleware.cors import CORSMiddleware

from app.services.binance_client import binance, client


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


@app.get('/')
async def hello():
    # trade_info = client.get_all_coins_info()
    trade_info = client.get_exchange_info()['symbols']
    tickers = client.get_ticker()
    btc_traded_coins = [
        symbol['symbol'] for symbol in trade_info
        if symbol['quoteAsset'] == 'BTC' and symbol['status'] == 'TRADING']
    pairs_info = []
    for ticker in tickers:
        if ticker['symbol'] in btc_traded_coins:

            pairs_info.append({
                'pair': f'{ticker['symbol'][:-len('BTC')]}/{ticker['symbol'][-len('BTC'):]}',
                '24h_change': ticker['priceChangePercent'],  
                'last_price': ticker['lastPrice']           
            })

    return sorted(pairs_info[0:20], key=lambda x: x['pair'])
    # order_book = binance.get_order_book_info('BTCUSDT')
    # coins_trades = binance.get_recent_trades('BTCUSDT')
    # coins_info = binance.get_traded_pair_info('BTCUSDT')
    # # print(type(order_book['bids'][0][0])) - > str
    # # return {'coinsInfo': coins_info,
    # #         # 'orderBook': order_book,
    # #         'trades': coins_trades
    # #         }

app.include_router(stream_router)
app.include_router(auth_router)
app.include_router(coins_router)
