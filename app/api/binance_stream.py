from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from app.services.binance_client import binance
import asyncio

router = APIRouter()
# print(client.get_symbol_ticker("BTCUSDT"))

@router.websocket('/trade/{traded_pair}')
async def stream_trade(websocket: WebSocket, traded_pair):
    
    await websocket.accept()
    pair= ('').join(traded_pair.split("-"))
    step = 17

    try:
        while step:
            coins_info = binance.get_traded_pair_info(traded_pair=pair)
          
            data = {
                'coinsInfo': coins_info,
                'orderBook':''
            }

        
            await websocket.send_json(data)
            step= step-1
            await asyncio.sleep(1)
        
    except WebSocketDisconnect:
        print("Stopped")