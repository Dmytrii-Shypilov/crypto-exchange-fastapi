from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from app.services.authorization import auth
from app.services.binance_client import BinanceTrade
from datetime import datetime
from typing import List
from binance import Client
from app.services.binance_client import client


class PaperTradeClient(BinanceTrade):
    def __init__(self, client: Client):
        super().__init__(client)
        self.cached_data = {'orders': [], 'trades': []}

    def get_orders(self) -> List[dict]:
        return self.cached_data['orders']

    def add_order(self, order: dict):
        self.cached_data['orders'].append(order)

    def remove_order(self, order_id: str):
        self.cached_data['orders'] = [
            order for order in self.cached_data['orders'] if str(order['_id']) != order_id]

    def get_all_data(self):
        return self.cached_data

    def get_trades(self) -> List[dict]:
        return self.cached_data['trades']

    def add_trade(self, trade):
        self.cached_data['trades'].append(trade)

    def remove_trade(self, trade_id):
        self.cached_data['trades'] = [
            trade for trade in self.cached_data['trades'] if str(trade['_id']) != trade_id]

    def fill_cached_data(self, orders=[], trades=[]):
        self.cached_data['trades'] = trades
        self.cached_data['orders'] = orders

    def is_cache_empty(self):
        return True if len(self.cached_data['orders']) == 0 and len(self.cached_data['orders']) == 0 else False
    
    def fill_the_limit_order(self, hist_trades: List[dict], order: dict):
        my_trades = []
        remaining_amount = float(order['amount'])  # Initialize remaining amount Base
        remaining_total = float(order['total'])   # Initialize remaining total Quote total
        for trade in hist_trades:
            if order['side'] == 'buy' and not trade['isBuyerMaker']:
                if trade['price'] <= order['price']:
                    trade_amount = float(trade['qty'])
                    trade_total = float(trade['quoteQty'])
                    # Handle full match for this trade 9
                    if remaining_amount >= trade_amount:
                        remaining_amount -= trade_amount
                        remaining_total -= trade_total
                    
                        partially_filled_trade = {
                            'orderTime': order['orderTime'],
                            'pair': order['pair'],
                            'type': order['type'],
                            'side' : order['side'],
                            'executed': int(datetime.now().timestamp() * 1000),
                            'price': order['price'],
                            'amount': trade_amount, 
                            'total': trade_total
                        }
                        my_trades.append(partially_filled_trade)
                    elif remaining_amount < trade_amount:
                       
                        fully_filled_trade =  {
                            'orderTime': order['orderTime'],
                            'pair': order['pair'],
                            'type': order['type'],
                            'side' : order['side'],
                            'executed': int(datetime.now().timestamp() * 1000),
                            'price': order['price'],
                            'amount': remaining_amount,
                            'total': remaining_total
                        }
                        my_trades.append(fully_filled_trade)
                        break
                    if remaining_amount <= 0:
                        break
        if remaining_amount  > 0:
            order.update({'total': remaining_total, 'amount': remaining_amount, 'filled': float(order['amount']) - remaining_amount }) 
        else:
            order = None          
        return order, my_trades


class PaperTradeManager:
    def __init__(self):
        self.user_clients = {}

    def get_client(self, user_id: str) -> PaperTradeClient:
        if user_id not in self.user_clients:
            self.user_clients[user_id] = PaperTradeClient()
        return self.user_clients[user_id]


paper_trader = PaperTradeManager()




# 1. General Principles of Order Matching:
# Limit Orders: These orders specify the maximum price you're willing to buy (or the minimum price you're willing to sell).

# A buy limit order will only execute at your specified price or lower.
# A sell limit order will only execute at your specified price or higher.
# Matching Priority: Orders are matched based on:

# Price: Best price gets priority.
# Time: If prices are the same, the earlier order takes priority (FIFO: First In, First Out).
# Order Book Structure:

# The bid side contains buy orders, sorted from highest price to lowest.
# The ask side contains sell orders, sorted from lowest price to highest.
# Partial Fills: If the market offers a smaller quantity at your limit price, only part of your 
# order will be executed. The remainder will stay in the order book until it's matched or canceled.