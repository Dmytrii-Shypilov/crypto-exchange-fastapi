from pydantic import BaseModel
from bson import ObjectId

class User(BaseModel):
    firstName: str
    lastName: str
    email: str
    is_active: bool

    # Define Pydantic model with ObjectId support
    # This is optional if you need ObjectId serialization
    # You can convert ObjectId to str when working with it, as FastAPI will handle the serialization automatically.
    id: str  # The user ID will be returned as a string

    class Config:
        # Allow Pydantic to handle ObjectId as string
        json_encoders = {
            ObjectId: str
        }