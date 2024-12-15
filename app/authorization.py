from datetime import timedelta, datetime
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from app.db.mongo_session import get_collection
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()


ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = os.getenv("ENCR_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

# Hash password
def get_password_hash(password: str):
    return pwd_context.hash(password)

# Verify password
def verify_password(plain_password: str, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Create JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Authentication helper function
# Retrieves and validates the currently authenticated user based on a JWT (JSON Web Token).
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload =jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get('sub')
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await get_collection('users').find_one({'_id': ObjectId(user_id)})
        if user is None:
            raise HTTPException(status_code=401, detail='User not found')
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid token')