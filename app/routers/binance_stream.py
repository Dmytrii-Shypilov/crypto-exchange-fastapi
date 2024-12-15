from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from app.services.binance_client import binance
import asyncio

stream_router = APIRouter()

@stream_router.websocket('/trade/{traded_pair}')
async def stream_trade(websocket: WebSocket, traded_pair: str):
    await websocket.accept()
    pair = ''.join(traded_pair.split("-"))

    try:
        while True:  # Continuous stream
            try:
                # Fetch data from Binance
                order_book = binance.get_order_book_info(traded_pair=pair)
                coins_info = binance.get_traded_pair_info(traded_pair=pair)
            except Exception as e:
                print(f"Error fetching Binance data: {e}")
                await websocket.close(code=1011)  # Internal server error
                return

            # Construct and send data
            data = {
                'coinsInfo': coins_info,
                'orderBook': order_book,
            }
            await websocket.send_json(data)
            await asyncio.sleep(0.5)  # Avoid spamming the client

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for pair: {traded_pair}")
    except WebSocketException as e:
        print(f"WebSocket exception: {e}")
        await websocket.close()
    finally:
        print(f"Connection closed for pair: {traded_pair}")
