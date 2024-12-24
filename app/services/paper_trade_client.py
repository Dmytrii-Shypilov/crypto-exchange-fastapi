from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from app.services.authorization import auth
import asyncio
from datetime import datetime
from typing import List


class PaperTradeClient:
    def __init__(self):
        self.cached_orders = []
    
    def get_orders(self) -> List[dict]:
        return self.cached_orders
    
    def add_order(self, order: dict):
        self.cached_orders.append(order)

    def remove_order(self, order_id: str):
        self.cached_orders = [order for order in self.cached_orders if str(order['_id']) != order_id]


class PaperTradeManager:
    def __init__(self):
        self.user_clients = {}

    def get_client(self, user_id: str) -> PaperTradeClient:
        if user_id not in self.user_clients:
            self.user_clients[user_id] = PaperTradeClient()
        return self.user_clients[user_id] 
    

paper_trader = PaperTradeManager()