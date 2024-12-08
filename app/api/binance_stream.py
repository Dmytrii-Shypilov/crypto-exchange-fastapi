from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from app.services.binance_client import client
import asyncio

router = APIRouter()
# print(client.get_symbol_ticker("BTCUSDT"))

@router.websocket('/trade/{traded_pair}')
async def stream_trade(websocket: WebSocket, traded_pair):
    print('WEBSOCKET')
    await websocket.accept()
    print('WEBSOCKET')
    try:
        while True:
            ticker = client.get_symbol_ticker(traded_pair)
            print(ticker)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Stopped")