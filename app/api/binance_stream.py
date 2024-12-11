from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from app.services.binance_client import binance
import asyncio

stream_router = APIRouter()
# print(client.get_symbol_ticker("BTCUSDT"))


@stream_router.websocket('/trade/{traded_pair}')
async def stream_trade(websocket: WebSocket, traded_pair):

    await websocket.accept()
    pair = ('').join(traded_pair.split("-"))
    step = 27

    try:
        prevPrice = '0'
        while step:
            order_book = binance.get_order_book_info(traded_pair=pair)
            coins_info = binance.get_traded_pair_info(traded_pair=pair)
            

            # price_movement = 1 if float(prevPrice.replace(',', '')) < float(coins_info['lastPrice'].replace(',', '')) else 0 if float(
            #     prevPrice.replace(',', '')) == float(coins_info['lastPrice'].replace(',', '')) else -1
            # prevPrice = coins_info['lastPrice']
            # coins_info.update({'priceMove': price_movement})

            data = {
                'coinsInfo': coins_info,
                'orderBook': order_book
            }

            await websocket.send_json(data)
            step = step-1
            # await asyncio.sleep(1)

    except WebSocketDisconnect:
        print("Stopped")
