from fastapi import FastAPI
from app.routers.binance_stream import stream_router
from app.routers.auth import auth_router
from app.routers.coins import coins_router
from app.routers.paper_trade import paper_trade_router
from fastapi.middleware.cors import CORSMiddleware

from app.services.binance_client import binance, client

from datetime import datetime


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
    trades = binance.get_recent_trades('BTCUSDT')
    timestamp = trades[-1]['time']
    id = trades[-1]['id']
    timestamp_sec = timestamp/ 1000

    # Convert to a datetime object
    dt_object = datetime.fromtimestamp(timestamp_sec)

    # Format the datetime object into a readable string
    readable_date = dt_object.strftime("%Y-%m-%d %H:%M:%S")
    return trades, [id, timestamp]




app.include_router(stream_router)
app.include_router(auth_router)
app.include_router(coins_router)
app.include_router(paper_trade_router)
