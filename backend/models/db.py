import os
import pymongo
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

load_dotenv()

# Use a default DB name if not specified in the URI
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/arp_ids_db")

# Module-level singleton — lazy-initialized
_db = None
_client = None
_db_initialized = False


def get_db():
    """Return the MongoDB database handle, creating the connection if needed."""
    global _db, _client, _db_initialized
    if _db_initialized:
        return _db          # may be None if previous attempt failed

    _db_initialized = True  # prevent repeated connection storms on failure
    try:
        # tlsCAFile is crucial for MongoDB Atlas connections on many systems
        _client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where()
        )

        # Verify the connection is successful
        _client.admin.command('ping')

        # Get the database from URI or default to 'arp_ids_db'
        _db = _client.get_default_database()
        if _db is None:
            _db = _client["arp_ids_db"]

        print(f"[INFO] Connected to MongoDB: {_db.name}")

        # Essential Indexes (idempotent — create_index is a no-op if already exists)
        try:
            _db.users.create_index("email", unique=True)
            _db.alerts.create_index("alert_id", unique=True)
            _db.alerts.create_index([("timestamp", pymongo.DESCENDING)])
        except Exception as e:
            print(f"[WARN] Index creation issue (non-fatal): {e}")

        return _db
    except Exception as e:
        print(f"[ERROR] MongoDB Connection Failed: {e}")
        _db = None
        return None


def get_db_status():
    """Return True if the database connection is alive."""
    try:
        if _client is not None:
            _client.admin.command('ping')
            return True
    except Exception:
        pass
    return _db is not None


def reconnect_db():
    """Force a reconnection attempt (e.g. after transient network failure)."""
    global _db_initialized
    _db_initialized = False
    return get_db()


# Initialize the connection once at module import
db = get_db()