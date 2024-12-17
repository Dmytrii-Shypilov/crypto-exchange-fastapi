from fastapi import FastAPI
from app.routers.binance_stream import stream_router
from app.routers.auth import auth_router
from fastapi.middleware.cors import CORSMiddleware

from app.services.binance_client import binance


app = FastAPI()

origins = [
    "http://localhost:5173",  # Frontend development server
    # "https://your-production-domain.com",  # Production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific origins
    allow_credentials=True,  # Allow cookies or authentication headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# @app.get('/')
# async def hello():
#     order_book = binance.get_order_book_info('BTCUSDT')
#     coins_trades = binance.get_recent_trades('BTCUSDT')
#     coins_info = binance.get_traded_pair_info('BTCUSDT')
    
    
   
#     # print(type(order_book['bids'][0][0])) - > str
#     return {'coinsInfo': coins_info,
#             # 'orderBook': order_book,
#             'trades': coins_trades 
#             }

app.include_router(stream_router)
app.include_router(auth_router)
