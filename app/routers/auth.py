from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.authorization import create_access_token, get_password_hash, verify_password
from app.db.mongo_session import get_collection
from app.schemas import Token