import os, sys
# Ensure the backend package root is importable in all execution contexts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time


class Alert:
    _collection = None

    @classmethod
    def get_collection(cls):
        if cls._collection is None:
            try:
                from models.db import db, reconnect_db
                current_db = db
                if current_db is None:
                    current_db = reconnect_db()
                if current_db is not None:
                    cls._collection = current_db.alerts
                    # Optimization: Create indexes (idempotent)
                    try:
                        cls._collection.create_index([("timestamp", -1)])
                        cls._collection.create_index([("alert_id", 1)], unique=True)
                    except Exception as e:
                        print(f"[WARN] Alert index creation issue: {e}")
            except Exception as e:
                print(f"[ERROR] Failed to get alerts collection: {e}")
        return cls._collection

    @staticmethod
    def log_alert(alert_data):
        collection = Alert.get_collection()
        if collection is not None:
            try:
                # Upsert ensures that if an alert_id already exists, it just updates 
                # instead of creating a duplicate or crashing.
                return collection.update_one(
                    {"alert_id": alert_data.get("alert_id")},
                    {"$set": alert_data},
                    upsert=True
                )
            except Exception as e:
                print(f"[ERROR] Failed to log alert to MongoDB: {e}")
                # Reset collection ref so next call retries the connection
                Alert._collection = None
        else:
             print("[WARN] Database not connected. Alert logged to console only.")
             print(f"  -> {alert_data}")
        return None

    @staticmethod
    def get_recent_alerts(limit=100):
        collection = Alert.get_collection()
        if collection is not None:
            try:
                # Excluding '_id' ensures the result is JSON-serializable for the frontend
                return list(collection.find({}, {'_id': 0}).sort("timestamp", -1).limit(limit))
            except Exception as e:
                print(f"[ERROR] Failed to fetch recent alerts: {e}")
                Alert._collection = None
        return []
    
    @staticmethod
    def get_active_attackers():
         collection = Alert.get_collection()
         if collection is not None:
              try:
                  # Get alerts from the last 60 seconds
                  one_min_ago = time.time() - 60
                  recent = list(collection.find({"timestamp": {"$gte": one_min_ago}}, {'_id': 0}))
                  ips = list(set([a["ip"] for a in recent if "ip" in a]))
                  return ips
              except Exception as e:
                  print(f"[ERROR] Failed to fetch active attackers: {e}")
                  Alert._collection = None
         return []
    
    @staticmethod
    def clear_all():
        collection = Alert.get_collection()
        if collection is not None:
            try:
                collection.delete_many({})
            except Exception as e:
                print(f"[ERROR] Failed to clear alerts: {e}")
                Alert._collection = None