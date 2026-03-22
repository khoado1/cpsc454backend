"""
Run once to create a user in MongoDB:
  python create_user.py <username> <password>
"""
import sys
import os
import bcrypt
from pymongo import MongoClient
from db import MONGODB_URI, APP_DB_NAME, USERS_COLLECTION_NAME

client = MongoClient(MONGODB_URI)
db = client[APP_DB_NAME]
users = db[USERS_COLLECTION_NAME]

if len(sys.argv) != 3:
    print("Usage: python create_user.py <username> <password>")
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2].encode("utf-8")
password_hash = bcrypt.hashpw(password, bcrypt.gensalt())

if users.find_one({"username": username}):
    print(f"User '{username}' already exists.")
    sys.exit(1)

users.insert_one({"username": username, "password_hash": password_hash})
print(f"User '{username}' created successfully.")
