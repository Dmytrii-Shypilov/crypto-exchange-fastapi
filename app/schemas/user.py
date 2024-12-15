from pydantic import BaseModel, EmailStr

# A schema in FastAPI typically refers to Pydantic models, which are used to define and validate the structure of data. 

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    email: EmailStr
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str