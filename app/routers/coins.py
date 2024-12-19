from fastapi import APIRouter, HTTPException, Response, Request
from fastapi.encoders import jsonable_encoder
from app.db.mongo_session import get_collection
from app.services.binance_client import binance
from app.services.authorization import decode_access_token
from bson import ObjectId


coins_router = APIRouter(prefix='/coins', tags=["TradedCoins"])

@coins_router.get('/{quoteAsset}')
async def get_traded_coins(quoteAsset: str,request: Request):
    try:
       
        token = request.cookies.get('access_token')
 
        if not token:
            raise HTTPException(status_code=401, detail="Token not found")
        decoded_data = decode_access_token(token)
    
        user_id = decoded_data.get('sub')
     
        if not user_id:
           
            raise HTTPException(status_code=401, detail="Invalid token: user ID missing")
        fav_collection = get_collection('favorite_pairs')
       
        fav_coins = await fav_collection.find_one({'owner': ObjectId(user_id)})
        traded_pairs = binance.get_traded_pairs(quoteAsset=quoteAsset)
        
        return {
            'favCoins':fav_coins['favPairs'],
            'tradedPairs': traded_pairs
        }
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
