from datetime import timedelta, datetime
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, Response, Request
from fastapi.security import OAuth2PasswordBearer
from app.db.mongo_session import get_collection
from bson import ObjectId
from dotenv import load_dotenv
import bcrypt
import os

load_dotenv()


# ACCESS_TOKEN_EXPIRE_MINUTES = 60
SECRET_KEY = os.getenv("ENCR_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


# pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

class AuthManager:
    def __init__(self, secret_key: str, algorithm: str):
        self.SECRET_KEY = secret_key
        self.ALGORITHM = algorithm
    # Hash password
    def get_password_hash(self, password: str):
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')
        # return pwd_context.hash(password)

    # Verify password
    def verify_password(self, plain_password: str, hashed_password):
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        # return pwd_context.verify(plain_password, hashed_password)

    # Create JWT token
    def create_token(self,data: dict, expires_delta: timedelta = timedelta(minutes=15)):
        to_encode = data.copy()
        expire = datetime.now() + expires_delta
        to_encode.update({'exp': expire})
        print(self.SECRET_KEY)
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def add_tokens_to_cookies(self, response: Response, access_token, refresh_token):
        response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=True, #True
        samesite='None', #Strict
        max_age=45*60
    )

        response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite='None',
        max_age=5*24*60*60
        )

    def validate_token(self, token: str):
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload.get('exp') and datetime.fromtimestamp(payload['exp']) < datetime.now():
                raise HTTPException(status_code=401, detail="Token has expired")
            user_id = payload.get('sub')
            return user_id
        except JWTError as e:
            raise HTTPException(status_code=401, detail="Invalid token") from e
        
    def authenticate_user(self ,request: Request):
        token = request.cookies.get('access_token')
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Access token cookie missing"
        )   
        user_id = auth.validate_token(token)
        if not user_id:
            raise HTTPException(
            status_code=401,
                detail="Invalid or expired token"
            )
        return user_id


auth = AuthManager(secret_key=SECRET_KEY, algorithm=ALGORITHM)

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