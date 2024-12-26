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
            order for order in self.cached_data['orders'] if str(order['_id']) != order_id]
        
    def update_order(self, order_id,update: dict):
        for order in self.cached_data['orders']:
            if order['_id'] == order_id:
                order.update(update)

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
    
    def retrieve_order_match_periods(self, order):
        interval = client.KLINE_INTERVAL_30MINUTE
        all_klines_since_order = self.client.get_klines(symbol=order['pair'], interval=interval, startTime= order['orderTime'])
        filtered_klines= []
        if order['side'] == 'sell':
            filtered_klines = [{'from': kline[0], 'to': kline[6]} for kline in all_klines_since_order if float(kline[2]) >= float(order['price'])]
        elif order['side'] == 'buy':
            filtered_klines = [{'from': kline[0], 'to': kline[6]} for kline in all_klines_since_order if float(kline[3]) <= float(order['price'])] 

        return filtered_klines
        
    
    def fill_the_limit_order(hist_trades: List[dict], order: dict):
        my_trades = []
        remaining_amount = Decimal(order['amount'])  # Base currency amount (e.g., BTC)
        remaining_total = Decimal(order['total'])   # Quote currency total (e.g., USDT)
        
        # Ensure trades are sorted once by price before filtering
        sorted_trades = sorted(hist_trades, key=lambda x: float(x['price']), reverse=(order['side'] == 'sell'))
        
        if order['side'] == 'buy':
            if float(sorted_trades[0]['price']) <= float(order['price']):
                # Filter trades where isBuyerMaker is False and price <= order's price
                filtered_trades = [trade for trade in sorted_trades if not trade['isBuyerMaker'] and float(trade['price']) <= float(order['price'])]
            else:
                # If the lowest price in sorted trades is higher than the order price, no matches
                return order, my_trades
        
        # Handle 'sell' orders
        elif order['side'] == 'sell':
            if float(sorted_trades[-1]['price']) >= float(order['price']):
                # Filter trades where isBuyerMaker is True and price >= order's price
                filtered_trades = [trade for trade in sorted_trades if trade['isBuyerMaker'] and float(trade['price']) >= float(order['price'])]
            else:
                # If the highest price in sorted trades is lower than the order price, no matches
                return order, my_trades

        # If there are no matching trades, return the original order
        if not filtered_trades:
            return order, my_trades
    
        # Loop through filtered trades to fill the order
        for trade in filtered_trades:
            trade_price = Decimal(trade['price']) # Round price to 2 decimal places for precision
            trade_amount = Decimal(trade['qty'])  # Round qty to 6 decimal places for precision
            trade_total = Decimal(trade['quoteQty']) # Round quoteQty to 2 decimal places
            print(remaining_amount,remaining_total)
            if order['side'] == 'buy' and not trade['isBuyerMaker']:
                if remaining_amount >= trade_amount:
                    remaining_amount -= trade_amount
                    remaining_total -= trade_total
                    partially_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade_price,
                        'amount': trade_amount,
                        'total': trade_total
                    }
                    my_trades.append(partially_filled_trade)
                else:
                    partial_trade_total = remaining_amount * trade_price
                    fully_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade_price,
                        'amount': remaining_amount,
                        'total': partial_trade_total
                    }
                    my_trades.append(fully_filled_trade)
                    remaining_amount = 0
                    remaining_total = 0
                    print(remaining_amount, remaining_total)
                    # print(trade['price'], order['price'], order['side'], fully_filled_trade)
                    break

            elif order['side'] == 'sell' and trade['isBuyerMaker']:
                if remaining_amount >= trade_amount:
                    remaining_amount -= trade_amount
                    remaining_total -= trade_total
                    partially_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade_price,
                        'amount': trade_amount,
                        'total': trade_total
                    }
                    my_trades.append(partially_filled_trade)
                
                else:
                    partial_trade_total = remaining_amount * trade_price
                    fully_filled_trade = {
                        'orderTime': order['orderTime'],
                        'pair': order['pair'],
                        'type': order['type'],
                        'side': order['side'],
                        'executed': int(datetime.now().timestamp() * 1000),
                        'price': trade_price,
                        'amount': remaining_amount,
                        'total': partial_trade_total
                    }
                    
                    my_trades.append(fully_filled_trade)
                
                    remaining_amount = 0
                    remaining_total = 0
                    break

            # Stop processing if the order is fully filled
            if remaining_amount <= 0:
                break

        # After processing, if there is remaining amount, the order is partially filled
        if remaining_amount > 0:
            order.update({
                'total': remaining_total,
                'amount': remaining_amount,
                'filled': float(order['amount']) - remaining_amount,
                'latestTradeId': filtered_trades[-1]['id']
            })
        else:
            # Order is fully filled, return None
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