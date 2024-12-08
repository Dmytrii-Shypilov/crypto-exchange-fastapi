from fastapi import FastAPI
from app.api.binance_stream import router 

from app.services.binance_client import binance


app = FastAPI()



@app.get('/')
async def hello():
    data = binance.get_traded_pair_info('BTCUSDT')
    # print(data)
    return data

app.include_router(router)