import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.db import db
from pymongo.errors import DuplicateKeyError

class User:
    _collection = None

    @classmethod
    def get_collection(cls):
        if cls._collection is None and db is not None:
            cls._collection = db.users
        return cls._collection

    @staticmethod
    def create_user(user_data):
        collection = User.get_collection()
        if collection is not None:
            try:
                # The 'email' unique index in db.py will protect against duplicates here
                result = collection.insert_one(user_data)
                return result.inserted_id
            except DuplicateKeyError:
                print(f"[WARN] User creation failed: Email {user_data.get('email')} already exists.")
                return "exists"
            except Exception as e:
                print(f"[ERROR] Failed to create user: {e}")
        return None

    @staticmethod
    def get_user_by_email(email):
        collection = User.get_collection()
        if collection is not None:
            return collection.find_one({"email": email})
        return None

    @staticmethod
    def get_user_by_id(user_id):
        collection = User.get_collection()
        if collection is not None:
            # Note: Ensure user_id is passed as a BSON ObjectId if querying by MongoDB's _id
            return collection.find_one({"_id": user_id})
        return None