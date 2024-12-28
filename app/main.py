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



@app.get('/')
async def hello():
    print('Hello')
     # price= 98472
    lat_id = '4332450816'
    price = Decimal('96300')
    base = Decimal('0.23')
    tot_quote = price * base
    my_order_2 = {'orderTime': int((datetime.now() - timedelta(hours=10)).timestamp() * 1000), 'type': 'limit', 'pair': 'BTCUSDT',
                    'side': 'buy', 'price': price, 'amount': base, 'total': tot_quote, 'latestTradeId': lat_id}
  

    

app.include_router(stream_router)
app.include_router(auth_router)
app.include_router(coins_router)
app.include_router(paper_trade_router)
