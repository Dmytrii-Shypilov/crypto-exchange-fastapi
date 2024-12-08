from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import os

PASSWORD = os.getenv("DB_PASSWORD")

uri = f'mongodb+srv://dmytriishypilov:{
    PASSWORD}@coinstatusdb.rqxu7.mongodb.net/?retryWrites=true&w=majority&appName=CoinstatusDB'

client = MongoClient(uri,  server_api=ServerApi('1'))

# try:
#     print(client.server_info())  # Will raise an error if the connection fails
#     print('GOOOOOOOOOOOOOOOOOOOOOOOOOOD')
# except Exception as e:
#     print(f"Connection failed: {e}")
# print(uri)

# getting  our db

def deserialize_object(obj):
    return {
        'id': str(obj['_id']),
        'name': obj['name'],
        'email': obj['email'],
        'password': obj['password']
    }

def desereialize_series(series):
    return [deserialize_object(obj) for obj in series]

# CoinstatusDB is the Cluster Name
# Database is 'trading' or 'sample_mflix' (mock)


db = client['sample_mflix']
# Getting the collection from the db
collection = db['users']

# print(client.list_database_names())
# print(db.list_collection_names())

#checking num of documents in the collection
print(collection.count_documents({}))

cursor = collection.find().limit(5)

print(desereialize_series(cursor))
