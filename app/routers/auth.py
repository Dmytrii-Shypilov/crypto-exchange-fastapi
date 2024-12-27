from fastapi import APIRouter, HTTPException, Response, Request
from app.services.authorization import auth
from app.db.mongo_session import get_collection
from app.schemas.user import User, UserSignup, UserLogin


auth_router = APIRouter(prefix='/auth', tags=['Authentication'])


@auth_router.post('/signup')
async def signup_user(user: UserSignup, response: Response):

    user_collection = get_collection('users')
    fav_coins = get_collection('favorite_pairs')

    existing_user = await user_collection.find_one({'email': user.email})

    if existing_user:
        raise HTTPException(status_code=400, detail='Email already registered')

    hashed_password = auth.get_password_hash(user.password)
    new_user = {'firstName': user.firstName, 'lastName': user.lastName, 'email': user.email,
                'hashed_password': hashed_password, 'is_active': True}
    result = await user_collection.insert_one(new_user)
    _id = result.inserted_id

    fav_coins.insert_one({'owner': _id, 'favPairs': []})

    access_token = auth.create_token(data={'sub': str(_id)})
    refresh_token = auth.create_token(data={'sub': str(_id)})
    auth.add_tokens_to_cookies(response,access_token=access_token, refresh_token=refresh_token)

    return {'firstName': new_user['firstName'], 'lastName': new_user['lastName'], 'email': new_user['email'], 'is_active': new_user['is_active'], 'id': str(_id)}


@auth_router.post('/login')
async def login_user(payload: UserLogin, response: Response):
    user_collection = get_collection('users')
    user = await user_collection.find_one({'email': payload.email})
    if user:
        password_verified = auth.verify_password(payload.password, user['hashed_password'])
    if not user or not password_verified:
        raise HTTPException(status_code=400, detail='Invalid credentials')
    access_token = auth.create_token(data={'sub': str(user['_id'])})
    refresh_token = auth.create_token(data={'sub': str(user['_id'])})
    auth.add_tokens_to_cookies(response,access_token=access_token, refresh_token=refresh_token)

    return {'firstName': user['firstName'], 'lastName': user['lastName'], 'email': user['email'], 'id': str(user['_id'])}


@auth_router.post('/current')
async def get_current_user(request: Request):
    try:
        token = request.cookies.get('access_token')
        if not token:
            raise HTTPException(status_code=401, detail="Token not found")
        user_id = auth.validate_token(token)
       
        user_collection = get_collection('users')
        user = await user_collection.find_one({'_id': user_id})
        if not user:
            raise HTTPException(status_code=404, detail='User no found')
        return {'firstName': user['firstName'], 'lastName': user['lastName'], 'email': user['email'], 'id':str(user['_id'])}

    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')


@auth_router.post('/logout')
async def logout_user(response: Response):
    print('LOGOUT')
    response.delete_cookie(key='access_token', httponly=True,
                           secure=True, samesite='Strict')
    response.delete_cookie(key='refresh_token',
                           httponly=True, secure=True, samesite='Strict')
    return {'isLoggedOut': True}

