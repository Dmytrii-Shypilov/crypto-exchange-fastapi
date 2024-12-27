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
connection = 0

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

# @paper_trade_router.websocket('/stream/{user_id}',)
# async def paper_trade_stream(websocket: WebSocket, user_id: str):

#     global connection
#     if user_id in active_connections:
#         raise HTTPException(status_code=400, detail="WebSocket connection already exists for this user.")
#     await websocket.accept()
#     connection +=1
#     active_connections[user_id] = websocket
#     trader = paper_trader.get_client(user_id)
#     # getting collections from the database
#     orders_collection = get_collection('orders')
#     trades_collection = get_collection('trades')
#     print(active_connections)
#     # add data to the cache
#     db_orders = await orders_collection.find().to_list(length=None)
#     trader.fill_cached_data(trades=[], orders=db_orders)
#     # print(trader.get_all_data())
#     print(db_orders)
#     await asyncio.sleep(3)
#     try:
#         while True:          
#             orders = f" my_id: {user_id} conn: {connection} my_orders{len(trader.get_orders())}"
#             # print(active_connections)
#             # print(orders)
       
#        # Checking each order for fulfillment
#         for order in trader.cached_data['orders']:
#             lattest_trade_id = order['lattestTradeId']
#             print(f"============={trader.cached_data['orders'].index(order)+1} of {len(trader.cached_data['orders'])}===============")
#             print("=======================================================")
#             print(f"ORDER: {order}")
#             # moving through all trades since the lattest trade id this order was posted
#             while lattest_trade_id:
#                 hist_trades = trader.client.get_historical_trades(symbol=order['pair'], limit=500, fromId=lattest_trade_id)

#                 # stop loop iteration when there is no or little trades
#                 if hist_trades == [] or len(hist_trades) < 250:
#                     break
                
#                 # check for 'limit' order fulfillment
#                 if order['type'] == 'limit':
#                     final_order, trades = trader.fill_the_limit_order(hist_trades, order)
#                 # remove order from cache and db if it is fully filled (final_order == None)  
#                 print(f"final_oreder: {final_order}, trades: {trades}")
#                 if not final_order:
#                     trader.remove_order(order_id=order['_id'])
#                 else:
#                     trader.update_order(final_order)
#                 # update trades database if any trade took place
#                 if len(trades) > 0:
#                     await trades_collection.insert_many(trades) 
#                 await asyncio.sleep(2)
#         # delay next loop iteration if there is no order in cache
#         if len(trader.cached_data['orders']) == 0:
#             await asyncio.sleep(30)
       
#     except WebSocketDisconnect:
#         active_connections[user_id].remove(websocket)
#         if not active_connections[user_id]:
#             del active_connections[user_id]
#         print(f"User {user_id} disconnected")
#         await websocket.close()
#         print('Paper trade disconnected')
#     except WebSocketException as e:
#         print(f"WebSocket exception: {e}")
#         # Remove the WebSocket connection when closed
#         del active_connections[user_id]
#         await websocket.close()

@paper_trade_router.websocket('/stream/{user_id}')
async def paper_trade_stream(websocket: WebSocket, user_id: str):
    if user_id in active_connections:
        # await websocket.close(code=4001)
        raise HTTPException(status_code=400, detail="WebSocket connection already exists for this user.")
    
    await websocket.accept()
    active_connections[user_id] = websocket
    trader = paper_trader.get_client(user_id)

    orders_collection = get_collection('orders')
    trades_collection = get_collection('trades')

    db_orders = await orders_collection.find({'owner': user_id}).to_list(length=None)
    print(f"DB ORDERS: {db_orders}")
    trader.fill_cached_data(trades=[], orders=db_orders)
   
    try:
        while True:
            if len(trader.cached_data['orders']):

                for order in trader.cached_data['orders']:
                    print(f"============={trader.cached_data['orders'].index(order)+1} of {len(trader.cached_data['orders'])}===============")
                    print("=======================================================")
                    print(f"ORDER: {order}")
                    order['pair'] = order['pair'].replace('/', '')
                    lattest_trade_id = order['latestTradeId']
                    while True:
                        hist_trades = list(trader.client.get_historical_trades(
                            symbol=order['pair'], limit=500, fromId=lattest_trade_id
                        ))
                        # print(f'HIST TRADES {hist_trades[0]['id']}')
                        
                        if not hist_trades or len(hist_trades) < 250:
                            break

                        if order['type'] == 'Limit':
                            print("LIMIT")
                        
                            final_order, trades = trader.fill_the_limit_order(hist_trades, order=order)
                            
                        print(f"FINAL_ORDER: {final_order}")
                        if not final_order:
                            trader.remove_order(order_id=order['_id'])
                        else:
                            trader.update_order(final_order['_id'],final_order)
                           

                        if trades:
                            await trades_collection.insert_many(trades)
                        lattest_trade_id = int(lattest_trade_id)+500
                        # await asyncio.sleep(2)

            if not trader.cached_data['orders']:
                print('NO ORDERS')
                await asyncio.sleep(30)

    except WebSocketDisconnect:
        del active_connections[user_id]
        print(f"User {user_id} disconnected")
        await websocket.close()
    except Exception as e:
        print(f"Error: {e}")
        del active_connections[user_id]
        await websocket.close()



@paper_trade_router.post('/postOrder')
async def post_order(order: dict,user_id: str = Depends(auth.authenticate_user)):
    trader = paper_trader.get_client(user_id)
    orders_collection = get_collection('orders')
    pair = order['pair'].replace('/', '')
    lattest_trade_id = binance.get_lattest_trade_id(pair)
    order_time = int(datetime.now().timestamp() * 1000)
    total = float(order['price']) * float(order['amount'])
    order.update({'latestTradeId': lattest_trade_id, 'orderTime': order_time ,'filled': 0, 'total': total, 'owner': user_id})
    posted_order = await orders_collection.insert_one(order)
    order.update({'_id': posted_order.inserted_id})
    trader.add_order(order)
    


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