from binance import Client
import os

API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv("SECRET_KEY")


client = Client(API_KEY, SECRET_KEY)


trades = client.get_order_book(symbol='BTCUSDT', limit=100)
print(trades)
print(API_KEY)
print(SECRET_KEY)