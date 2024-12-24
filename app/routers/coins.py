from fastapi import APIRouter, HTTPException, Request
from app.db.mongo_session import get_collection
from app.services.binance_client import binance
from app.services.authorization import auth
from bson import ObjectId


coins_router = APIRouter(prefix='/coins', tags=["TradedCoins"])

@coins_router.get('/getFavs')
async def get_favorite_coins(request: Request):
        try:
            token = request.cookies.get('access_token')

            if not token:
                raise HTTPException(status_code=401, detail="Token not found")
            user_id = auth.validate_token(token)

            if not user_id:

                raise HTTPException(
                    status_code=401, detail="Invalid token: user ID missing")
            fav_collection = get_collection('favorite_pairs')
            fav_coins = await fav_collection.find_one({'owner': ObjectId(user_id)})
            return {'favCoins': fav_coins['favPairs'],}
        except Exception:
             raise HTTPException(status_code=401, detail='Invalid or expired token')


@coins_router.get('/{quoteAsset}')
async def get_traded_coins(quoteAsset: str, request: Request):
    try:

        token = request.cookies.get('access_token')

        if not token:
            raise HTTPException(status_code=401, detail="Token not found")
        user_id = auth.validate_token(token)

       

        if not user_id:

            raise HTTPException(
                status_code=401, detail="Invalid token: user ID missing")
      
        traded_pairs = binance.get_traded_pairs(quoteAsset=quoteAsset)

        return {
            'tradedPairs': traded_pairs
        }
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')




@coins_router.post('/addFav/{pair}')
async def add_favorite_pair(pair: str, request: Request):
    try:
        token = request.cookies.get('access_token')
       
        if not token:
            raise HTTPException(status_code=401, detail="Token not found")
        user_id = auth.validate_token(token)
       

        if not user_id:
            raise HTTPException(
                status_code=401, detail="Invalid token: user ID missing")
        
        fav_collection = get_collection('favorite_pairs')
        result  = fav_collection.update_one(
            {"owner": ObjectId(user_id)},
            # $addToSet to avoid duplicates
            {"$addToSet": {"favPairs": pair.replace('-', '/')}},
            upsert=True  # Create the document if it doesn't exist
        )
        if result.modified_count == 0 and result.upserted_id is None:
            raise HTTPException(status_code=500, detail="Failed to add the favorite pair")
        
        return {'message': f"{pair} pair is added"}
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')


@coins_router.delete('/removeFav/{pair}')
async def remove_favorite_pair(pair: str, request: Request):
    try:
        # Get the access token from cookies
        token = request.cookies.get('access_token')
        if not token:
            raise HTTPException(status_code=401, detail="Token not found")

        # Decode the token to extract user data
        user_id = auth.validate_token(token)
       
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: user ID missing")

        # Access the MongoDB collection
        fav_collection = get_collection('favorite_pairs')

        # Convert user_id to ObjectId if necessary
        owner_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id

        # Update the document: Remove the pair from the favPairs array
        result = fav_collection.update_one(
            {"owner": owner_id},
            {"$pull": {"favPairs":  pair.replace('-', '/')}}  # Use $pull to remove the pair
        )

        # Check if the update was successful
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Pair not found or not in favorites")

        return {"message": "Favorite pair removed successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
