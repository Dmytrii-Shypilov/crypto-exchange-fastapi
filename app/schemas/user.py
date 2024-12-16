from pydantic import BaseModel, EmailStr
from bson import ObjectId
# A schema in FastAPI typically refers to Pydantic models, which are used to define and validate the structure of data. 

class User(BaseModel):
    firstName: str
    lastName: str
    email: str
    is_active: bool
    id: str  # The user ID will be returned as a string


class UserSignup(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str
    

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    email: EmailStr
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str

    class Config:
        # Allow Pydantic to handle ObjectId as string
        json_encoders = {
            ObjectId: str
        }