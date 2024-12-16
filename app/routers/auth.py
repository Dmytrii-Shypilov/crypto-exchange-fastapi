from fastapi import APIRouter, Depends, HTTPException, Response, Request
from app.authorization import create_access_token, create_refresh_token, get_password_hash, verify_password, decode_access_token
from app.db.mongo_session import get_collection
from app.schemas.user import User, UserSignup, UserLogin


auth_router = APIRouter(prefix='/auth', tags=['Authentication'])


@auth_router.post('/signup')
async def signup_user(user: UserSignup, response: Response):
    user_collection = get_collection('users')
    existing_user = await user_collection.find_one({'email': user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    hashed_password = get_password_hash(user.password)
    new_user = {'firstName': user.firstName, 'lastName': user.lastName,
                'hashed_password': hashed_password, 'is_active': True}
    result = await user_collection.insert_one(new_user)
    _id = result.inserted_id
    access_token = create_access_token(data={'sub': str(_id)})
    refresh_token = create_refresh_token(data={'sub': str(_id)})

    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=True,
        samesite='Strict',
        max_age=15*60
    )

    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite='Strict',
        max_age=30*60
    )

    return User(firstName=new_user['firstName'], lastName=new_user['lastName'], email=new_user['email'], is_active=new_user['is_active'], id=_id)


@auth_router.post('/login')
async def login_user(payload: UserLogin, response: Response):
    user_collection = get_collection('users')
    user = await user_collection.find_one({'email': payload.email})
    password_verified = verify_password(
        payload.password, user['hashed_password'])
    if not user and not password_verified:
        raise HTTPException(status_code=400, detail='Invalid credentials')
    access_token = create_access_token(data={'sub': str(user['_id'])})
    refresh_token = create_refresh_token(data={'sub': str(user['_id'])})
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=True,
        samesite='Strict',
        max_age=15*60
    )

    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite='Strict',
        max_age=5*24*60*60
    )
    return User(firstName=user['firstName'], lastName=user['lastName'], email=user['email'], is_active=user['is_active'], id=str(user['_id']))


@auth_router.post('/current')
async def get_current_user(request: Request):
    try:
        token = request.cookies.get('access_token')
        if not token:
            raise HTTPException(status_code=401, detail="Token not found")
        decoded_data = decode_access_token(token)
        user_id = decoded_data.get('sub')
        user_collection = get_collection('users')
        user = await user_collection.find_one({'_id': user_id})
        if not user:
            raise HTTPException(status_code=404, detail='User no found')
        return User(firstName=user['firstName'], lastName=user['lastName'], email=user['email'], is_active=user['is_active'], id=str(user['_id']))

    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

@auth_router.post('/logout')
async def logout_user(response: Response):
    response.delete_cookie(key='access_token', httponly=True, secure=True, samesite='Strict')
    response.delete_cookie(key='refresh_token', httponly=True, secure=True, samesite='Strict')
    return {'message': "Logged out"}