from fastapi import APIRouter, HTTPException, Request, Depends
from app.db.mongo_session import get_collection
from app.services.binance_client import binance
from app.services.authorization import decode_access_token
from datetime import datetime, timezone
from bson import ObjectId
from fastapi.encoders import jsonable_encoder


cached_orders = []

def convert_objectid_to_str(doc):
    if isinstance(doc, dict):
        return {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in doc.items()}
    return doc

def authenticate_user(request: Request):
    token = request.cookies.get('access_token')
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Access token cookie missing"
        )
    
    # Simulate Token Validation Logic

    decoded_data = decode_access_token(token)
    user_id = decoded_data.get('sub')
    if not user_id:
        raise HTTPException(
        status_code=401,
            detail="Invalid or expired token"
        )

    return user_id

paper_trade_router = APIRouter(
    prefix='/paperTrade', 
    tags=['Paper Trade'],
    dependencies=[Depends(authenticate_user)]
    )

@paper_trade_router.post('/postOrder')
async def post_order(order: dict,user_id: str = Depends(authenticate_user)):
    orders_collection = get_collection('orders')
    pair = order['pair'].replace('/', '')
    lattest_trade_id = binance.get_lattest_trade_id(pair)
    order_time = int(datetime.now().timestamp() * 1000)
    total = float(order['price']) * float(order['amount'])
    order.update({'lattestTradeId': lattest_trade_id, 'orderTime': order_time ,'filled': 0, 'total': total, 'owner': user_id})
    posted_order = await orders_collection.insert_one(order)
    order.update({'_id': posted_order.inserted_id})
    cached_orders.append(order)
    


@paper_trade_router.get('/getOrders')
async def get_orders(user_id: str = Depends(authenticate_user)):
    orders_collection = get_collection('orders')
    orders_cursor = orders_collection.find({'owner': user_id})
    orders = await orders_cursor.to_list(length=None)
    if not orders:
            return []
    orders = [convert_objectid_to_str(order) for order in orders]
    return orders


@paper_trade_router.delete('/cancelOrder/{orderId}')
async def cancel_order(orderId: str, request: Request):
    print(orderId)
    orders_collection = get_collection('orders')
    result = await orders_collection.find_one_and_delete({'_id': ObjectId(orderId)})
    return {'deleted': orderId}