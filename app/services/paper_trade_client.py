from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from app.services.authorization import auth
from app.services.binance_client import BinanceTrade
from datetime import datetime
from typing import List
from binance import Client
from decimal import Decimal
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
            order for order in self.cached_data['orders'] if order['_id'] != order_id]
        
    def update_order(self, order_id,update: dict):
        for order in self.cached_data['orders']:
            if order['_id'] == order_id:
                order.update(update)

    def get_all_data(self):
        return self.cached_data

    def get_trades(self) -> List[dict]:
        return self.cached_data['trades']

    def add_trades(self, trades: List):
        self.cached_data['trades'].extend(trades)

    def remove_trade(self, trade_id):
        self.cached_data['trades'] = [
            trade for trade in self.cached_data['trades'] if trade['_id'] != trade_id]

    def fill_cached_data(self, orders=[], trades=[]):
        self.cached_data['trades'] = trades
        self.cached_data['orders'] = orders

    def is_cache_empty(self):
        return True if len(self.cached_data['orders']) == 0 and len(self.cached_data['orders']) == 0 else False
    
    def is_price_relevant(self, order):
        interval = client.KLINE_INTERVAL_1HOUR
        all_klines_since_order = self.client.get_klines(symbol=order['pair'], interval=interval, startTime= order['orderTime'])
        if order['side'] == 'sell':
            filtered_klines = [kline for kline in all_klines_since_order if Decimal(kline[2]) >= Decimal(order['price'])]                          
        elif order['side'] == 'buy':
            filtered_klines = [kline for kline in all_klines_since_order if Decimal(kline[3]) <= Decimal(order['price'])] 
        rec_trades = self.client.get_recent_trades(symbol=order['pair'])
        return {'isRelevant': bool(len(filtered_klines)), 'latestTradeId': int(rec_trades[0]['id']) - 1000 } 
        
    
    def fill_the_limit_order(self, order: dict):
        state = {
            'side': order['side'],
            'searchExhausted': False,
            'fillComplete': False,
            'latestTradeId': order['latestTradeId'],
            'myTrades': [],
            'remAmount': Decimal(order['amount']),
            'remTotal': Decimal(order['total']),
            'balance': {
                'orderTotal': Decimal(order['total']),
                'orderAmount': Decimal(order['amount']),
                'tradesTotal':Decimal('0'),
                'tradesAmount': Decimal('0'),
            }
        }

        # price_match = self.is_price_relevant(order=order)
        # if not price_match['isRelevant']:
        #     state['latestTradeId'] = price_match['latestTradeId']
        #     state['searchExhausted'] =True
        #     return state

        while not state['fillComplete'] and not state['searchExhausted']:
        
            hist_trades = self.client.get_historical_trades(
                symbol='BTCUSDT', fromId=state['latestTradeId'], limit=1000)
            # Exit loop if no more trades
            if not len(hist_trades) :
                state['searchExhausted'] = True
                break

            # Sort trades by price (ascending for buy, descending for sell)
            sorted_trades = sorted(
                hist_trades, 
                key=lambda x: Decimal(x['price']), 
                reverse=(order['side'] == 'sell')
            )
            # Filter trades based on side and price
            if order['side'] == 'buy':
                filtered_trades = [
                    trade for trade in sorted_trades 
                    if not trade['isBuyerMaker'] and Decimal(trade['price']) <= Decimal(order['price'])
                ]
            else:  # sell
                filtered_trades = [
                    trade for trade in sorted_trades 
                    if trade['isBuyerMaker'] and Decimal(trade['price']) >= Decimal(order['price'])
                ]

            # Update latestTradeId to the highest ID in current batch
            state['latestTradeId'] = int(hist_trades[-1]['id']) + 1
            print(f'Id: {state['latestTradeId']} histTrLen: {len(hist_trades)} filterdeLen: {len(filtered_trades)}' )
            # Skip to next iteration if no matching trades
            if not filtered_trades:
                continue

            # Process filtered trades
            for trade in filtered_trades:
                trade_price = Decimal(trade['price'])
                trade_amount = Decimal(trade['qty'])
                trade_total = trade_price * trade_amount

                if state['remAmount'] >= trade_amount:
                    # PArtial trade match
                
                    state['remAmount'] -= trade_amount
                    state['remTotal'] -= trade_total
                    state['myTrades'].append({
                        'pair': order['pair'],
                        'orderTime': order['orderTime'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade_price,
                        'amount': trade_amount,
                        'total': trade_total,
                    })
                    state['balance']['tradesTotal'] += trade_total
                    state['balance']['tradesAmount'] += trade_amount
                else:
                    # Full trade match if remAmount(order amount) < Trade Amount
                    partial_trade_total = state['remAmount'] * trade_price
                    state['myTrades'].append({
                        'pair': order['pair'],
                        'orderTime': order['orderTime'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade_price,
                        'amount': state['remAmount'],
                        'total': partial_trade_total,
                    })
                    state['balance']['tradesAmount'] += state['remAmount']
                    state['balance']['tradesTotal'] += partial_trade_total
                    state['remAmount'] = Decimal(0)
                    state['remTotal'] = Decimal(0)
                    state['fillComplete'] = True
                    
                    break

            # Stop processing if fully filled
            if state['fillComplete']:
                break
        state['balance'].update({'quoteDifference': state['balance']['tradesTotal'] - state['balance']['orderTotal']})
        # if order partially filled and trades are exxhausted => remAmount and remTotal are present in state 
        # to update the order amount an total fields in cache
        return  state

class PaperTradeManager:
    def __init__(self, client: Client):
        self.user_clients = {}
        self.client = client
    def get_client(self, user_id: str) -> PaperTradeClient:
        if user_id not in self.user_clients:
            self.user_clients[user_id] = PaperTradeClient(self.client)
        return self.user_clients[user_id]


paper_trader = PaperTradeManager(client=client)




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