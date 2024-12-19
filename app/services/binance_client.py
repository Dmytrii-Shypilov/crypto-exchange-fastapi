from binance import Client
from decimal import Decimal
import os


API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv("BIN_SECRET_KEY")

client = Client(API_KEY, SECRET_KEY)


class BinanceTrade:
    def __init__(self, client: Client):
        self.client = client

    def get_traded_pair_info(self, traded_pair: str):
        result = self.client.get_ticker(symbol=traded_pair)
        data = {
            'lastPrice': result['lastPrice'],
            'priceChange': result['priceChange'],
            'priceChangePercent': result['priceChangePercent'],
            'highPrice': result['highPrice'],
            'lowPrice': result['lowPrice'],
            'baseVolume': result['volume'],
            'quoteVolume': result['quoteVolume']
        }
        return data

    def get_recent_trades(self, trade_pair: str):
        result = self.client.get_recent_trades(symbol=trade_pair, limit=10)
        return result

    def get_order_book_info(self, traded_pair, limit=20):
        result = self.client.get_order_book(symbol=traded_pair, limit=limit)
        return result

    def get_traded_pairs(self, quoteAsset: str):
        print('method')
        symbols_info = self.client.get_exchange_info()['symbols']
        tickers = self.client.get_ticker()
        btc_traded_coins = [
        symbol['symbol'] for symbol in symbols_info
        if symbol['quoteAsset'] == quoteAsset and symbol['status'] == 'TRADING']
        pairs_info = []
        for ticker in tickers:
           if ticker['symbol'] in btc_traded_coins:

            pairs_info.append({
                'pair': f'{ticker['symbol'][:-len(quoteAsset)]}/{ticker['symbol'][-len(quoteAsset):]}',
                'change': ticker['priceChangePercent'],  
                'lastPrice': ticker['lastPrice']           
            })

        return sorted(pairs_info, key=lambda x: x['pair'])


binance = BinanceTrade(client)


# # Get the current price of a specific pair
# symbol = 'BTCUSDT'  # Replace with your desired trading pair
# current_price = client.get_symbol_ticker(symbol=symbol)

# # Get 24-hour ticker statistics for a specific pair
# stats = client.get_ticker(symbol=symbol)
# print(f"24h Change: {stats['priceChangePercent']}%")
# print(f"24h Volume: {stats['volume']}")
# print(f"24h High: {stats['highPrice']}")
# print(f"24h Low: {stats['lowPrice']}")

# # Get the order book for a specific pair
# order_book = client.get_order_book(symbol=symbol, limit=5)  # Adjust limit as needed (5, 10, 20, 50, 100, 500, or 1000)
# print("Top 5 Bids:", order_book['bids'])
# print("Top 5 Asks:", order_book['asks'])

# # Get all trading pairs for a specific base coin
# base_coin = 'BTC'  # Replace with your desired base coin
# exchange_info = client.get_exchange_info()
# trading_pairs = [
#     symbol['symbol'] for symbol in exchange_info['symbols'] if symbol['quoteAsset'] == base_coin
# ]

# Retrives trades from the fromId(soecific trade id in the past) 500 trades forward
# batch = client.get_historical_trades(symbol=symbol, limit=500, fromId=last_trade_id)
