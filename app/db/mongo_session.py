from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Fetch database credentials
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_CLUSTER = os.getenv("DB_CLUSTER")
DB_NAME = os.getenv("DB_NAME")

# Database URI
uri = f'mongodb+srv://{DB_USERNAME}:{DB_PASSWORD}@{DB_CLUSTER}/?retryWrites=true&w=majority&appName={DB_NAME}'

# Connect to MongoDB asynchronously
client = AsyncIOMotorClient(uri)
db = client[DB_NAME]

# Collection getting function
def get_collection(collection_name: str):
    return db[collection_name]







# # try:
# #     print(client.server_info())  # Will raise an error if the connection fails
# #     print('GOOOOOOOOOOOOOOOOOOOOOOOOOOD')
# # except Exception as e:
# #     print(f"Connection failed: {e}")
# # print(uri)

# # getting  our db

# def deserialize_object(obj):
#     return {
#         'id': str(obj['_id']),
#         'name': obj['name'],
#         'email': obj['email'],
#         'password': obj['password']
#     }

# def desereialize_series(series):
#     return [deserialize_object(obj) for obj in series]

# # CoinstatusDB is the Cluster Name
# # Database is 'trading' or 'sample_mflix' (mock)


# db = client['sample_mflix']
# # Getting the collection from the db
# collection = db['users']

# # print(client.list_database_names())
# # print(db.list_collection_names())

# #checking num of documents in the collection
# print(collection.count_documents({}))

# cursor = collection.find().limit(5)

# print(desereialize_series(cursor))
