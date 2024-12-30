from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket, WebSocketException, WebSocketDisconnect
from app.services.paper_trade_client import paper_trader
from app.db.mongo_session import get_collection
from app.services.binance_client import binance
from app.services.authorization import auth
from app.db.mongo_session import get_collection
from datetime import datetime
from bson import ObjectId
import asyncio

active_connections = {}
background_tasks = {}

 # uvicorn app.main:app --reload

def convert_objectid_to_str(doc):
    if isinstance(doc, dict):
        return {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in doc.items()}
    return doc


paper_trade_router = APIRouter(
    prefix='/paperTrade', 
    tags=['Paper Trade'],
    # dependencies=[Depends(auth.authenticate_user)]
    )

async def process_orders(user_id: str):
        # check where it is better to fetch orders from the database
        trader = paper_trader.get_client(user_id)
        orders_collection = get_collection('orders')

        while True:
            if not trader.cached_data['orders']:
                print(f"No orders for user {user_id}. Stopping the loop.")
                break  # Exit loop if no orders
            # check each order for filling
            for order in trader.cached_data['orders']:
                order['pair'] = order['pair'].replace('/', '')
                if order['type'] == 'Limit':
                    print('Processing limit order')
                    result = trader.fill_the_limit_order(order=order)
                    # if the order is fully filled
                    if result['fillComplete']:
                        trader.remove_order(order_id=order['_id'])
                        await orders_collection.find_one_and_delete({'_id': order['_id']})
                    elif len(result['myTrades']):
                        update = {
                            'amount': str(result['remAmount']),
                            'total': str(result['remTotal']),
                            'latestTradeId': result['latestTradeId']
                        }
                        order.update(update)
                        await orders_collection.find_one_and_update({'_id': order['_id']}, {'$set': update})


@paper_trade_router.websocket('/stream/{user_id}')
async def paper_trade_stream(websocket: WebSocket, user_id: str):              
    try:
        if user_id in active_connections:
            raise HTTPException(status_code=400, detail="WebSocket connection already exists for this user.")

        await websocket.accept()

        # add websocket to the active connections
        active_connections[user_id] = websocket

        # Start the background task only when orders exist
        if user_id not in background_tasks:
            background_tasks[user_id] = asyncio.create_task(process_orders(user_id=user_id))

        while True:
            await asyncio.sleep(10)  # Keep the WebSocket alive

    except WebSocketDisconnect:
        print(f"User {user_id} disconnected")
    finally:
        # Cleanup
        active_connections.pop(user_id, None)
        if user_id in background_tasks:
            background_tasks[user_id].cancel()
            del background_tasks[user_id]
        await websocket.close()



@paper_trade_router.post('/postOrder')
async def post_order(order: dict, user_id: str = Depends(auth.authenticate_user)):
    trader = paper_trader.get_client(user_id)
    orders_collection = get_collection('orders')
    
    # Generate order details
    pair = order['pair'].replace('/', '')
    latest_trade_id = binance.get_lattest_trade_id(pair)
    order_time = int(datetime.now().timestamp() * 1000)
    total = float(order['price']) * float(order['amount'])
    order.update({'latestTradeId': latest_trade_id, 'orderTime': order_time, 
                  'filled': 0, 'total': total, 'owner': user_id})
    
    # Insert order into database
    posted_order = await orders_collection.insert_one(order)
    order.update({'_id': posted_order.inserted_id})
    
    # Add order to trader's cache
    trader.add_order(order)
    
    # Dynamically start the background task if not running
    if user_id in active_connections and user_id not in background_tasks:
        # get certain user websocket session for sending any realated messages 
        websocket = active_connections[user_id]
        background_tasks[user_id] = asyncio.create_task(websocket.send_json({"message": "Starting order processing"}))
        background_tasks[user_id] = asyncio.create_task(process_orders(user_id=user_id))

    return {"success": True, "order": order}

    


@paper_trade_router.get('/getOrders')
async def get_orders(user_id: str = Depends(auth.authenticate_user)):
    orders_collection = get_collection('orders')
    orders_cursor = orders_collection.find({'owner': user_id})
    orders = await orders_cursor.to_list(length=None)
    if not orders:
            return []
    orders = [convert_objectid_to_str(order) for order in orders]
    return orders


@paper_trade_router.delete('/cancelOrder/{orderId}')
async def cancel_order(orderId: str, request: Request, user_id: str = Depends(auth.authenticate_user)):
    orders_collection = get_collection('orders')
    trader = paper_trader.get_client(user_id)
    try:
        await orders_collection.find_one_and_delete({'_id': ObjectId(orderId)})
        trader.remove_order(orderId)
    except Exception as e:
        print(e)
    return {'deleted': orderId}

@paper_trade_router.get('/closeStream')
def close_paper_trade_stream( request: Request):
    user_id = auth.authenticate_user(request=request)
    del active_connections[user_id]
    print(active_connections)





# @paper_trade_router.websocket('/stream/{user_id}')
# async def paper_trade_stream(websocket: WebSocket, user_id: str):
#     try:
#         if user_id in active_connections:
#             # await websocket.close(code=4001)
#             raise HTTPException(status_code=400, detail="WebSocket connection already exists for this user.")
        
#         await websocket.accept()
#         active_connections[user_id] = websocket
#         # set trader with its unique cache instance for the current user
#         trader = paper_trader.get_client(user_id)

#         # connect to the db orders/trades collections
#         orders_collection = get_collection('orders')
#         trades_collection = get_collection('trades')

#         # fetch orders from db and fill the cache (Initial one-time fetch)
#         db_orders = await orders_collection.find({'owner': user_id}).to_list(length=None)
#         trader.fill_cached_data(trades=[], orders=db_orders)

#         # start loop where cache is always checked for the present orders to be filled
#         while True:          
#             # check if there are orders available for check
#             if not len(trader.cached_data['orders']):
#                 print('NO ORDERS')
#                 await asyncio.sleep(5)
#                 # start new cycle if there are no orders found
#                 continue

#             # print(f"CACHED ORDERS: {trader.cached_data['orders']}")
#             # await asyncio.sleep(2)

#             for order in trader.cached_data['orders']:
#                 order['pair'] = order['pair'].replace('/', '')
#                 # check if the order's type is 'limit'
#                 if order['type'] == 'Limit':
#                     print('Limit')
#                     result = trader.fill_the_limit_order(order=order)

#                     # Convert all Decimal values to float before inserting
#                     if len(result['myTrades']):
#                         for trade in result['myTrades']:
#                             trade['price'] = float(trade['price'])
#                             trade['amount'] = float(trade['amount'])
#                             trade['total'] = float(trade['total'])



#                     if result['fillComplete']:
#                         # remove order from cache and db 
#                         trader.remove_order(order_id=order['_id'])
#                         await orders_collection.find_one_and_delete({'_id': order['_id']})
#                         # add trades to cache and db
#                         trader.add_trades(result['myTrades'])
#                         await trades_collection.insert_many(result['myTrades'])
#                     elif not result['fillComplete'] and len(result['myTrades']):
#                         # update order if partially filled
#                         update = {'amount': str(result['remAmount']), 'total': str(result['remTotal']), 'latestTradeId': result['latestTradeId']}
#                         # update order for cache and db
#                         order.update(update)
#                         await orders_collection.find_one_and_update({'_id': order['_id']}, {'$set': update})
#                         # add trades to cache and d
#                         trader.add_trades(result['myTrades'])
#                         await trades_collection.insert_many(result['myTrades'])
#                     # print(order)            
#                     # print(result)
#     except WebSocketDisconnect:
#         del active_connections[user_id]
#         print(f"User {user_id} disconnected")
#         await websocket.close()
#     except Exception as e:
#         print(f"Error: {e}")
#         del active_connections[user_id]
#         await websocket.close()
