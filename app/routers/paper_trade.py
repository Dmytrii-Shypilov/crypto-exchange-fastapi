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

def convert_objectid_to_str(doc):
    if isinstance(doc, dict):
        return {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in doc.items()}
    return doc


paper_trade_router = APIRouter(
    prefix='/paperTrade', 
    tags=['Paper Trade'],
    # dependencies=[Depends(auth.authenticate_user)]
    )

@paper_trade_router.websocket('/stream/{user_id}',)
async def paper_trade_stream(websocket: WebSocket, user_id: str):

    global connection
    if user_id in active_connections:
        raise HTTPException(status_code=400, detail="WebSocket connection already exists for this user.")
    await websocket.accept()
    connection +=1
    active_connections[user_id] = websocket
    trader = paper_trader.get_client(user_id)
    # getting collections from the database
    orders_collection = get_collection('orders')
    trades_collection = get_collection('trades')
    
    # add data to the cache
    db_orders = await list(orders_collection.find())
    db_trades = await list(trades_collection.find())
    trader.fill_cached_data(trades=db_trades, orders=db_orders)
    print(trader.get_all_data())
    
    try:
        while user_id in active_connections:          
            orders = f" my_id: {user_id} conn: {connection} my_orders{len(trader.get_orders())}"
            print(active_connections)
            print(orders)
       
       # Checking each order for fulfillment
        for order in trader.cached_data['orders']:
            lattest_trade_id = order['lattestTradeId']
            # moving through all trades since the lattest trade id this order was posted
            while lattest_trade_id:
                hist_trades = trader.client.get_historical_trades(symbol=order['pair'], limit=500, fromId=lattest_trade_id)
                if hist_trades == []:
                    break
              
                if order['type'] == 'limit':
                    final_order, trades = trader.fill_the_limit_order(hist_trades, order)
                if not final_order:
                    trader.remove_order(order_id=order['_id'])
                else:
                    trader.update_order(final_order)


            await asyncio.sleep(2)
        await websocket.close()
    except WebSocketDisconnect:
        active_connections[user_id].remove(websocket)
        if not active_connections[user_id]:
            del active_connections[user_id]
        print(f"User {user_id} disconnected")
        await websocket.close()
        print('Paper trade disconnected')
    except WebSocketException as e:
        print(f"WebSocket exception: {e}")
        # Remove the WebSocket connection when closed
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
    order.update({'lattestTradeId': lattest_trade_id, 'orderTime': order_time ,'filled': 0, 'total': total, 'owner': user_id})
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